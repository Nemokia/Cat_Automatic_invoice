"""
Server-side rendered views for the invoice application.

Each view uses Django's session auth (login_required) and queries
models directly instead of going through the REST API.
"""
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from captcha.fields import CaptchaField
from django.views import View
from django.views.generic import (
    TemplateView, ListView, CreateView, UpdateView, DetailView, FormView
)

from decimal import Decimal, InvalidOperation
from types import SimpleNamespace

from accounts.models import SellerProfile
from banks.models import Bank, BankAccount
from banks.forms import BankAccountForm
from customers.models import Customer
from invoices.models import Invoice, InvoiceItem, InvoiceNumberSequence
from products.models import Product, PriceHistory

User = get_user_model()

# ---------------------------------------------------------------------------
# Captcha helpers — show captcha after N consecutive failed attempts
# ---------------------------------------------------------------------------
CAPTCHA_THRESHOLD = 4  # show captcha after this many failures


def _get_captcha_context(request, session_key):
    """Return context dict with captcha info if needed."""
    attempts = request.session.get(session_key, 0)
    needs_captcha = attempts >= CAPTCHA_THRESHOLD
    ctx = {
        'needs_captcha': needs_captcha,
        'captcha_attempts': attempts,
    }
    if needs_captcha:
        from captcha.models import CaptchaStore
        from captcha.helpers import captcha_image_url
        key = CaptchaStore.generate_key()
        ctx['captcha_key'] = key
        ctx['captcha_image_url'] = captcha_image_url(key)
    return ctx


def _record_failure(request, session_key):
    """Increment failure counter in session."""
    request.session[session_key] = request.session.get(session_key, 0) + 1


def _clear_failures(request, session_key):
    """Reset failure counter on success."""
    request.session.pop(session_key, None)


def _verify_captcha(request, session_key):
    """Verify captcha if required. Returns (ok, error_message)."""
    attempts = request.session.get(session_key, 0)
    if attempts < CAPTCHA_THRESHOLD:
        return True, ''

    # Use django-simple-captcha's verification
    from captcha.models import CaptchaStore
    from captcha.helpers import captcha_image_url

    captcha_0 = request.POST.get('captcha_0', '')
    captcha_1 = request.POST.get('captcha_1', '').strip()

    if not captcha_0 or not captcha_1:
        return False, 'کد امنیتی الزامی است'

    try:
        CaptchaStore.objects.get(
            hashkey=captcha_0,
            response__iexact=captcha_1,
        ).delete()
    except CaptchaStore.DoesNotExist:
        # Generate new captcha for the form
        return False, 'کد امنیتی اشتباه است'

    return True, ''


def _validate_invoice_post(data):
    """Shared server-side validation for invoice create/edit POSTs.

    Returns (invoice_like_for_rerender_or_None, errors_dict).
    Required: customer full name (first+last) and at least one line item.
    """
    errors = []
    name = data.get('customer_name', '').strip()
    if not name:
        errors.append('نام و نام خانوادگی مشتری الزامی است.')
    elif not name.replace('\u200c', ' ').strip():  # ZWNJ-only name
        errors.append('نام و نام خانوادگی مشتری الزامی است.')

    names = data.getlist('item_product_name[]')
    has_item = any(n.strip() for n in names)
    if not has_item:
        errors.append('حداقل یک قلم فاکتور با نام کالا وارد کنید.')

    return errors


def _is_ajax_share(request):
    """AJAX "save & share" submit (stays on the form page, gets JSON back)."""
    return bool(request.GET.get('share')) and \
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def _invoice_share_payload(invoice):
    """JSON payload for AJAX share: invoice saved + client-side PDF share URL."""
    return JsonResponse({
        'ok': True,
        'invoice_id': invoice.pk,
        'invoice_number': invoice.invoice_number,
        'pdf_url': reverse('frontend:invoice_pdf', kwargs={'pk': invoice.pk}),
    })


# ---------------------------------------------------------------------------
# Authentication views
# ---------------------------------------------------------------------------

class LoginView(View):
    """Login page — accepts username/phone/email + password, or OTP login."""

    SESSION_KEY = 'login_failures'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('frontend:dashboard')
        ctx = _get_captcha_context(request, self.SESSION_KEY)
        return render(request, 'frontend/login.html', ctx)

    def post(self, request):
        action = request.POST.get('action', 'password')

        if action == 'password':
            return self._password_login(request)
        elif action == 'otp_request':
            return self._otp_request(request)
        elif action == 'otp_verify':
            return self._otp_verify(request)
        else:
            messages.error(request, 'درخواست نامعتبر')
            return render(request, 'frontend/login.html')

    def _password_login(self, request):
        from django.db.models import Q

        # Check captcha first
        captcha_ok, captcha_err = _verify_captcha(request, self.SESSION_KEY)
        if not captcha_ok:
            messages.error(request, captcha_err)
            ctx = _get_captcha_context(request, self.SESSION_KEY)
            ctx['username'] = request.POST.get('username', '').strip()
            return render(request, 'frontend/login.html', ctx)

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # Find user by username, email, or phone
        user_obj = None
        if '@' in username:
            user_obj = User.objects.filter(email__iexact=username).first()
        elif username.isdigit() and len(username) >= 10:
            user_obj = User.objects.filter(phone=username).first()
        else:
            user_obj = User.objects.filter(username=username).first()

        if user_obj:
            user = authenticate(request, username=user_obj.username, password=password)
        else:
            user = None

        if user is not None:
            _clear_failures(request, self.SESSION_KEY)
            login(request, user)
            next_url = request.GET.get('next', reverse('frontend:dashboard'))
            return redirect(next_url)

        _record_failure(request, self.SESSION_KEY)
        messages.error(request, 'نام کاربری، ایمیل یا شماره موبایل یا رمز عبور اشتباه است')
        ctx = _get_captcha_context(request, self.SESSION_KEY)
        ctx['username'] = username
        return render(request, 'frontend/login.html', ctx)

    def _otp_request(self, request):
        from accounts.email_utils import validate_email_strict, create_otp, send_otp_email
        email = request.POST.get('email', '').strip().lower()

        is_valid, err = validate_email_strict(email)
        if not is_valid:
            messages.error(request, err)
            return render(request, 'frontend/login.html', {'otp_email': email, 'otp_step': 'email'})

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            # Don't reveal if email exists
            messages.success(request, 'اگر ایمیل در سیستم ثبت شده باشد، کد تأیید ارسال شد.')
            return render(request, 'frontend/login.html', {'otp_step': 'sent', 'otp_email': email})

        code = create_otp(user, 'login')
        send_otp_email(user, code, 'login')
        messages.success(request, 'کد تأیید به ایمیل شما ارسال شد.')
        return render(request, 'frontend/login.html', {'otp_step': 'sent', 'otp_email': email})

    def _otp_verify(self, request):
        from accounts.email_utils import verify_otp
        email = request.POST.get('email', '').strip().lower()
        code = request.POST.get('otp_code', '').strip()

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            messages.error(request, 'ایمیل یافت نشد')
            return render(request, 'frontend/login.html', {'otp_step': 'email'})

        is_valid, err = verify_otp(user, code, 'login')
        if not is_valid:
            messages.error(request, err)
            return render(request, 'frontend/login.html', {'otp_step': 'sent', 'otp_email': email})

        # OTP valid — log in
        login(request, user)
        next_url = request.GET.get('next', reverse('frontend:dashboard'))
        return redirect(next_url)


class RegisterView(View):
    """Registration page — creates a new user and logs them in."""

    SESSION_KEY = 'register_failures'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('frontend:dashboard')
        ctx = _get_captcha_context(request, self.SESSION_KEY)
        return render(request, 'frontend/register.html', ctx)

    def post(self, request):
        from accounts.email_utils import validate_email_strict

        # Check captcha first
        captcha_ok, captcha_err = _verify_captcha(request, self.SESSION_KEY)
        if not captcha_ok:
            messages.error(request, captcha_err)
            ctx = _get_captcha_context(request, self.SESSION_KEY)
            ctx.update({k: request.POST.get(k, '').strip() for k in
                        ['username', 'email', 'first_name', 'last_name', 'phone']})
            return render(request, 'frontend/register.html', ctx)

        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()

        context = {
            'username': username,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone,
        }

        # Validation
        if not username or not password:
            _record_failure(request, self.SESSION_KEY)
            messages.error(request, 'نام کاربری و رمز عبور الزامی است')
            context.update(_get_captcha_context(request, self.SESSION_KEY))
            return render(request, 'frontend/register.html', context)
        if password != password_confirm:
            _record_failure(request, self.SESSION_KEY)
            messages.error(request, 'رمز عبور و تکرار آن مطابقت ندارند')
            context.update(_get_captcha_context(request, self.SESSION_KEY))
            return render(request, 'frontend/register.html', context)
        if len(password) < 8:
            _record_failure(request, self.SESSION_KEY)
            messages.error(request, 'رمز عبور باید حداقل ۸ کاراکتر باشد')
            context.update(_get_captcha_context(request, self.SESSION_KEY))
            return render(request, 'frontend/register.html', context)
        if User.objects.filter(username=username).exists():
            _record_failure(request, self.SESSION_KEY)
            messages.error(request, 'نام کاربری قبلاً استفاده شده است')
            context.update(_get_captcha_context(request, self.SESSION_KEY))
            return render(request, 'frontend/register.html', context)

        # Email validation (optional but if provided, must be valid)
        email_not_provided = not email
        if email:
            is_valid, err = validate_email_strict(email)
            if not is_valid:
                _record_failure(request, self.SESSION_KEY)
                messages.error(request, err)
                context.update(_get_captcha_context(request, self.SESSION_KEY))
                return render(request, 'frontend/register.html', context)
            if User.objects.filter(email__iexact=email).exists():
                _record_failure(request, self.SESSION_KEY)
                messages.error(request, 'این ایمیل قبلاً ثبت شده است')
                context.update(_get_captcha_context(request, self.SESSION_KEY))
                return render(request, 'frontend/register.html', context)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        # Store phone via profile or user field if available
        if hasattr(user, 'phone'):
            user.phone = phone
            user.save()

        # Create empty seller profile
        SellerProfile.objects.get_or_create(user=user)

        _clear_failures(request, self.SESSION_KEY)
        login(request, user)
        messages.success(request, 'حساب کاربری با موفقیت ایجاد شد')

        # Warn if email not provided
        if email_not_provided:
            messages.warning(request, '⚠️ ایمیل ثبت نشده! برای بازیابی رمز عبور، لطفاً به تنظیمات بروید و ایمیل خود را ثبت کنید.')

        return redirect('frontend:dashboard')


@login_required
def logout_view(request):
    """Log the user out and redirect to the login page."""
    logout(request)
    return redirect('frontend:login')


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard_view(request):
    """Main dashboard with stats, recent invoices, and monthly revenue chart."""
    user = request.user
    invoices = Invoice.objects.filter(user=user)

    total_invoices = invoices.count()
    total_revenue = invoices.aggregate(total=Sum('final_amount'))['total'] or 0
    total_customers = Customer.objects.filter(user=user).count()
    total_products = Product.objects.filter(user=user).count()
    paid_invoices = invoices.filter(is_paid=True).count()
    unpaid_invoices = invoices.filter(is_paid=False).count()

    recent_invoices = invoices.select_related('customer')[:5]

    # Monthly revenue for the last 12 months (for Chart.js line chart)
    from django.db.models.functions import TruncMonth
    from datetime import date
    today = date.today()
    twelve_months_ago = today.replace(year=today.year - 1, day=1)

    monthly_data = (
        invoices
        .filter(invoice_date__gte=twelve_months_ago)
        .annotate(month=TruncMonth('invoice_date'))
        .values('month')
        .annotate(revenue=Sum('final_amount'), count=Count('id'))
        .order_by('month')
    )

    # Build a complete 12-month series (fill gaps with 0)
    import jdatetime
    month_labels = []
    month_revenues = []
    month_counts = []
    monthly_map = {m['month']: m for m in monthly_data}

    for i in range(12):
        # Go from 11 months ago to current month
        m = (today.month - 11 + i) % 12 + 1
        y = today.year if (today.month - 11 + i) >= 0 else today.year - 1
        if (today.month - 11 + i) <= 0:
            y = today.year - 1
        # Simpler: use dateutil-style offset
        from dateutil.relativedelta import relativedelta
        dt = (today.replace(day=1) - relativedelta(months=11 - i))
        key = dt.replace(day=1)
        entry = monthly_map.get(key)
        jalali = jdatetime.date.fromgregorian(year=key.year, month=key.month, day=1)
        month_labels.append(f'{jalali.month}/{jalali.year % 100}')
        month_revenues.append(float(entry['revenue']) if entry else 0)
        month_counts.append(entry['count'] if entry else 0)

    # Compare this month vs last month
    this_month_rev = month_revenues[-1] if month_revenues else 0
    last_month_rev = month_revenues[-2] if len(month_revenues) > 1 else 0
    if last_month_rev > 0:
        month_change_pct = round((this_month_rev - last_month_rev) / last_month_rev * 100, 1)
    else:
        month_change_pct = 100 if this_month_rev > 0 else 0

    context = {
        'total_invoices': total_invoices,
        'total_revenue': total_revenue,
        'total_customers': total_customers,
        'total_products': total_products,
        'paid_invoices': paid_invoices,
        'unpaid_invoices': unpaid_invoices,
        'recent_invoices': recent_invoices,
        'chart_labels': month_labels,
        'chart_revenues': month_revenues,
        'chart_counts': month_counts,
        'this_month_rev': this_month_rev,
        'last_month_rev': last_month_rev,
        'month_change_pct': month_change_pct,
    }
    return render(request, 'frontend/dashboard.html', context)


# ---------------------------------------------------------------------------
# Invoice views
# ---------------------------------------------------------------------------

class InvoiceListView(LoginRequiredMixin, ListView):
    """List all invoices for the logged-in user with search & filters."""
    model = Invoice
    template_name = 'frontend/invoices/list.html'
    context_object_name = 'invoices'
    paginate_by = 20

    def get_queryset(self):
        qs = Invoice.objects.filter(user=self.request.user)
        # Search
        q = self.request.GET.get('search', '').strip()
        if q:
            qs = qs.filter(
                Q(invoice_number__icontains=q) |
                Q(customer_name__icontains=q) |
                Q(customer_phone__icontains=q) |
                Q(bank_name__icontains=q) |
                Q(notes__icontains=q)
            ).distinct()
        # Date filters
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            qs = qs.filter(invoice_date__gte=date_from)
        if date_to:
            qs = qs.filter(invoice_date__lte=date_to)
        # Status filter
        status = self.request.GET.get('status')
        if status == 'paid':
            qs = qs.filter(is_paid=True)
        elif status == 'unpaid':
            qs = qs.filter(is_paid=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_query'] = self.request.GET.get('search', '')
        ctx['date_from'] = self.request.GET.get('date_from', '')
        ctx['date_to'] = self.request.GET.get('date_to', '')
        ctx['filter_status'] = self.request.GET.get('status', '')
        return ctx


class InvoiceCreateView(LoginRequiredMixin, View):
    """Create a new invoice — GET shows form, POST processes it."""

    def get(self, request):
        # Pre-fill seller info from profile
        profile, _ = SellerProfile.objects.get_or_create(user=request.user)
        context = {
            'customers': Customer.objects.filter(user=request.user),
            'products': Product.objects.filter(user=request.user),
            'banks': BankAccount.objects.filter(user=request.user),
            'bank_list': Bank.objects.all(),
            'seller_profile': profile,
            'invoice': None,
            'items': [],
        }
        return render(request, 'frontend/invoices/create.html', context)

    def post(self, request):
        data = request.POST

        # Get or create customer
        customer_id = data.get('customer')
        customer = None
        customer_name = ''
        customer_phone = ''
        customer_address = ''

        # Read typed values from POST first (always, for update logic)
        typed_name = data.get('customer_name', '').strip()
        typed_phone = data.get('customer_phone', '').strip()
        typed_address = data.get('customer_address', '').strip()

        # Server-side validation
        errors = _validate_invoice_post(data)
        if errors:
            for err in errors:
                messages.error(request, err)
            if _is_ajax_share(request):
                return JsonResponse({'ok': False, 'errors': errors}, status=400)
            profile, _ = SellerProfile.objects.get_or_create(user=request.user)
            ns = SimpleNamespace(
                customer_name=typed_name, customer_phone=typed_phone,
                customer_address=typed_address,
                invoice_date=data.get('invoice_date', ''),
                due_date=data.get('due_date', ''),
                invoice_tax_rate=data.get('invoice_tax_rate', '0'),
                discount_type=data.get('discount_type', ''),
                discount_value=data.get('discount_value', '0'),
                bank_name=data.get('bank_name', ''),
                card_number=data.get('card_number', ''),
                iban=data.get('iban', ''),
                account_holder=data.get('account_holder', ''),
                notes=data.get('notes', ''),
            )
            return render(request, 'frontend/invoices/create.html', {
                'customers': Customer.objects.filter(user=request.user),
                'products': Product.objects.filter(user=request.user),
                'banks': BankAccount.objects.filter(user=request.user),
                'bank_list': Bank.objects.all(),
                'seller_profile': profile,
                'invoice': ns,
                'items': [],
            })

        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id, user=request.user)
                # Default to DB values; override with typed values below if needed
                customer_name = typed_name or customer.full_name
                customer_phone = typed_phone or customer.phone
                customer_address = typed_address or customer.address
            except Customer.DoesNotExist:
                pass
        else:
            customer_name = typed_name
            customer_phone = typed_phone
            customer_address = typed_address

        # Smart customer resolution — mirrors InvoiceCreateSerializer logic
        update_existing = data.get('customer_update_existing') == '1'
        create_new = data.get('customer_create_new') == '1'

        if customer and update_existing and (customer_name or customer_phone):
            # User confirmed "same customer" with potentially different info → update
            from customers.matching import parse_full_name
            if customer_name:
                first, last = parse_full_name(customer_name)
                customer.first_name, customer.last_name = first, last
            if customer_phone:
                customer.phone = customer_phone
            if customer_address:
                customer.address = customer_address
            customer.save()
        elif not customer and customer_name:
            # No ID set — auto-create or auto-link
            from customers.matching import find_customer_match, parse_full_name
            match = find_customer_match(request.user, customer_name, customer_phone)
            primary = match.get('primary')
            status = match.get('status', 'none')

            if status == 'exact' and primary and not create_new:
                # Exact match found — auto-link existing customer
                customer = Customer.objects.get(pk=primary['id'])
            else:
                # New customer or unresolved conflict — create
                first, last = parse_full_name(customer_name)
                customer, _ = Customer.objects.get_or_create(
                    user=request.user,
                    first_name=first,
                    last_name=last,
                    phone=customer_phone,
                    defaults={'address': customer_address},
                )

        # Seller info
        profile, _ = SellerProfile.objects.get_or_create(user=request.user)
        seller_name = data.get('seller_name', '') or request.user.get_full_name()
        seller_business = data.get('seller_business', '') or profile.business_name
        seller_address = data.get('seller_address', '') or profile.address
        seller_phone = data.get('seller_phone', '') or profile.phone

        # Bank info — save to BankAccount if bank_name provided
        bank_account_id = data.get('bank_account')
        bank_name = data.get('bank_name', '')
        card_number = data.get('card_number', '')
        iban = data.get('iban', '')
        account_holder = data.get('account_holder', '')

        if bank_account_id:
            try:
                ba = BankAccount.objects.get(id=bank_account_id, user=request.user)
                bank_name = ba.bank.name
                card_number = ba.card_number
                iban = ba.iban
                account_holder = ba.account_holder
            except BankAccount.DoesNotExist:
                pass
        elif bank_name and (card_number or iban):
            # Auto-create bank account if bank_name + (card or iban) provided
            bank_obj, _ = Bank.objects.get_or_create(name=bank_name)
            BankAccount.objects.get_or_create(
                user=request.user, bank=bank_obj, card_number=card_number,
                defaults={'iban': iban, 'account_holder': account_holder},
            )

        invoice = Invoice.objects.create(
            user=request.user,
            invoice_number=InvoiceNumberSequence.get_next_number(request.user),
            customer=customer,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_address=customer_address,
            seller_name=seller_name,
            seller_business=seller_business,
            seller_address=seller_address,
            seller_phone=seller_phone,
            invoice_date=data.get('invoice_date', timezone.now().date()),
            due_date=data.get('due_date') or None,
            invoice_tax_rate=Decimal(data.get('invoice_tax_rate', 0) or 0),
            discount_type=data.get('discount_type', ''),
            discount_value=Decimal(data.get('discount_value', 0) or 0),
            bank_name=bank_name,
            card_number=card_number,
            iban=iban,
            account_holder=account_holder,
            notes=data.get('notes', ''),
            is_paid='is_paid' in data,
        )

        # Create line items
        product_names = data.getlist('item_product_name[]')
        product_ids = data.getlist('item_product_id[]')
        quantities = data.getlist('item_quantity[]')
        unit_prices = data.getlist('item_unit_price[]')
        tax_rates = data.getlist('item_tax_rate[]')
        units = data.getlist('item_unit[]')
        frequencies = data.getlist('item_frequency[]')

        for i, name in enumerate(product_names):
            if not name.strip():
                continue
            product = None
            if i < len(product_ids) and product_ids[i]:
                try:
                    product = Product.objects.get(id=product_ids[i], user=request.user)
                except Product.DoesNotExist:
                    pass

            # Auto-create product if not linked
            if not product and name.strip():
                product, _ = Product.objects.get_or_create(
                    user=request.user, name=name.strip(),
                    defaults={'unit': units[i] if i < len(units) else 'عداد'},
                )

            try:
                qty = Decimal(quantities[i]) if i < len(quantities) and quantities[i] else Decimal('1')
                price = Decimal(unit_prices[i]) if i < len(unit_prices) and unit_prices[i] else Decimal('0')
                tax = Decimal(tax_rates[i]) if i < len(tax_rates) and tax_rates[i] else Decimal('0')
            except (InvalidOperation, ValueError):
                qty, price, tax = Decimal('1'), Decimal('0'), Decimal('0')
            unit = units[i] if i < len(units) else 'عدد'
            frequency = frequencies[i] if i < len(frequencies) else ''

            # Save price history for the product
            if product and price > 0:
                PriceHistory.objects.get_or_create(
                    product=product, price=price,
                )

            item = InvoiceItem(
                invoice=invoice,
                product=product,
                product_name=name.strip(),
                quantity=qty,
                unit_price=price,
                tax_rate=tax,
                unit=unit,
                frequency=frequency,
                order=i,
            )
            item.save()

        invoice.calculate_totals()
        invoice.save()

        messages.success(request, 'فاکتور با موفقیت ایجاد شد')
        if _is_ajax_share(request):
            return _invoice_share_payload(invoice)
        if request.GET.get('print'):
            return redirect('frontend:invoice_print', pk=invoice.pk)
        if request.GET.get('share'):
            return redirect(f"{reverse('frontend:invoice_detail', kwargs={'pk': invoice.pk})}?share=1")
        return redirect('frontend:invoice_detail', pk=invoice.pk)


class InvoiceEditView(LoginRequiredMixin, View):
    """Edit an existing invoice."""

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
        items = invoice.items.all().order_by('order', 'id')
        profile, _ = SellerProfile.objects.get_or_create(user=request.user)
        context = {
            'invoice': invoice,
            'items': items,
            'customers': Customer.objects.filter(user=request.user),
            'products': Product.objects.filter(user=request.user),
            'banks': BankAccount.objects.filter(user=request.user),
            'bank_list': Bank.objects.all(),
            'seller_profile': profile,
        }
        return render(request, 'frontend/invoices/edit.html', context)

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
        data = request.POST

        # Update customer
        customer_id = data.get('customer')
        customer = None

        typed_name = data.get('customer_name', '').strip()
        typed_phone = data.get('customer_phone', '').strip()
        typed_address = data.get('customer_address', '').strip()

        # Server-side validation
        errors = _validate_invoice_post(data)
        if errors:
            for err in errors:
                messages.error(request, err)
            if _is_ajax_share(request):
                return JsonResponse({'ok': False, 'errors': errors}, status=400)
            # Re-render with submitted values so user sees what they typed
            invoice.customer_name = typed_name
            invoice.customer_phone = typed_phone
            invoice.customer_address = typed_address
            return render(request, 'frontend/invoices/edit.html', {
                'invoice': invoice,
                'items': invoice.items.all().order_by('order', 'id'),
                'customers': Customer.objects.filter(user=request.user),
                'products': Product.objects.filter(user=request.user),
                'banks': BankAccount.objects.filter(user=request.user),
                'bank_list': Bank.objects.all(),
                'seller_profile': SellerProfile.objects.filter(user=request.user).first(),
            })

        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id, user=request.user)
                invoice.customer = customer
                invoice.customer_name = typed_name or customer.full_name
                invoice.customer_phone = typed_phone or customer.phone
                invoice.customer_address = typed_address or customer.address
            except Customer.DoesNotExist:
                pass
        else:
            invoice.customer = None
            invoice.customer_name = typed_name
            invoice.customer_phone = typed_phone
            invoice.customer_address = typed_address

        # Smart customer resolution — mirrors InvoiceCreateSerializer logic
        update_existing = data.get('customer_update_existing') == '1'
        create_new = data.get('customer_create_new') == '1'

        if customer and update_existing and (invoice.customer_name or invoice.customer_phone):
            from customers.matching import parse_full_name
            if invoice.customer_name:
                first, last = parse_full_name(invoice.customer_name)
                customer.first_name, customer.last_name = first, last
            if invoice.customer_phone:
                customer.phone = invoice.customer_phone
            if invoice.customer_address:
                customer.address = invoice.customer_address
            customer.save()
        elif not customer and invoice.customer_name:
            from customers.matching import find_customer_match, parse_full_name
            match = find_customer_match(request.user, invoice.customer_name, invoice.customer_phone)
            primary = match.get('primary')
            status = match.get('status', 'none')

            if status == 'exact' and primary and not create_new:
                customer = Customer.objects.get(pk=primary['id'])
                invoice.customer = customer
            else:
                first, last = parse_full_name(invoice.customer_name)
                customer, _ = Customer.objects.get_or_create(
                    user=request.user,
                    first_name=first,
                    last_name=last,
                    phone=invoice.customer_phone,
                    defaults={'address': invoice.customer_address},
                )
                invoice.customer = customer

        # Seller info
        invoice.seller_name = data.get('seller_name', '') or request.user.get_full_name()
        invoice.seller_business = data.get('seller_business', '')
        invoice.seller_address = data.get('seller_address', '')
        invoice.seller_phone = data.get('seller_phone', '')

        # Bank info
        bank_account_id = data.get('bank_account')
        if bank_account_id:
            try:
                ba = BankAccount.objects.get(id=bank_account_id, user=request.user)
                invoice.bank_name = ba.bank.name
                invoice.card_number = ba.card_number
                invoice.iban = ba.iban
                invoice.account_holder = ba.account_holder
            except BankAccount.DoesNotExist:
                pass
        else:
            invoice.bank_name = data.get('bank_name', '')
            invoice.card_number = data.get('card_number', '')
            invoice.iban = data.get('iban', '')
            invoice.account_holder = data.get('account_holder', '')
            # Auto-create bank account if bank_name + (card or iban) provided
            if invoice.bank_name and (invoice.card_number or invoice.iban):
                bank_obj, _ = Bank.objects.get_or_create(name=invoice.bank_name)
                BankAccount.objects.get_or_create(
                    user=request.user, bank=bank_obj, card_number=invoice.card_number,
                    defaults={'iban': invoice.iban, 'account_holder': invoice.account_holder},
                )

        # Dates & financials
        invoice.invoice_date = data.get('invoice_date', invoice.invoice_date)
        invoice.due_date = data.get('due_date') or None
        invoice.invoice_tax_rate = Decimal(data.get('invoice_tax_rate', 0) or 0)
        invoice.discount_type = data.get('discount_type', '')
        invoice.discount_value = Decimal(data.get('discount_value', 0) or 0)
        invoice.notes = data.get('notes', '')
        invoice.is_paid = 'is_paid' in data
        invoice.save()

        # Rebuild line items
        invoice.items.all().delete()
        product_names = data.getlist('item_product_name[]')
        product_ids = data.getlist('item_product_id[]')
        quantities = data.getlist('item_quantity[]')
        unit_prices = data.getlist('item_unit_price[]')
        tax_rates = data.getlist('item_tax_rate[]')
        units = data.getlist('item_unit[]')
        frequencies = data.getlist('item_frequency[]')

        for i, name in enumerate(product_names):
            if not name.strip():
                continue
            product = None
            if i < len(product_ids) and product_ids[i]:
                try:
                    product = Product.objects.get(id=product_ids[i], user=request.user)
                except Product.DoesNotExist:
                    pass

            try:
                qty = Decimal(quantities[i]) if i < len(quantities) and quantities[i] else Decimal('1')
                price = Decimal(unit_prices[i]) if i < len(unit_prices) and unit_prices[i] else Decimal('0')
                tax = Decimal(tax_rates[i]) if i < len(tax_rates) and tax_rates[i] else Decimal('0')
            except (InvalidOperation, ValueError):
                qty, price, tax = Decimal('1'), Decimal('0'), Decimal('0')
            unit = units[i] if i < len(units) else 'عدد'
            frequency = frequencies[i] if i < len(frequencies) else ''

            item = InvoiceItem(
                invoice=invoice,
                product=product,
                product_name=name.strip(),
                quantity=qty,
                unit_price=price,
                tax_rate=tax,
                unit=unit,
                frequency=frequency,
                order=i,
            )
            item.save()

        invoice.calculate_totals()
        invoice.save()

        messages.success(request, 'فاکتور با موفقیت به‌روزرسانی شد')
        if _is_ajax_share(request):
            return _invoice_share_payload(invoice)
        if request.GET.get('print'):
            return redirect('frontend:invoice_print', pk=invoice.pk)
        if request.GET.get('share'):
            return redirect(f"{reverse('frontend:invoice_edit', kwargs={'pk': invoice.pk})}?share=1")
        return redirect('frontend:invoice_detail', pk=invoice.pk)


class InvoiceDetailView(LoginRequiredMixin, View):
    """Read-only invoice detail page."""

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
        items = invoice.items.all().order_by('order', 'id')
        context = {
            'invoice': invoice,
            'items': items,
        }
        return render(request, 'frontend/invoices/detail.html', context)


@login_required
def invoice_duplicate_view(request, pk):
    """Duplicate an existing invoice."""
    original = get_object_or_404(Invoice, pk=pk, user=request.user)
    new_invoice = Invoice.objects.create(
        user=request.user,
        invoice_number=InvoiceNumberSequence.get_next_number(request.user),
        customer=original.customer,
        customer_name=original.customer_name,
        customer_phone=original.customer_phone,
        customer_address=original.customer_address,
        seller_name=original.seller_name,
        seller_business=original.seller_business,
        seller_address=original.seller_address,
        seller_phone=original.seller_phone,
        invoice_date=timezone.now().date(),
        due_date=original.due_date,
        invoice_tax_rate=original.invoice_tax_rate,
        discount_type=original.discount_type,
        discount_value=original.discount_value,
        bank_name=original.bank_name,
        card_number=original.card_number,
        iban=original.iban,
        account_holder=original.account_holder,
        notes=original.notes,
    )
    for item in original.items.all():
        item.pk = None
        item.invoice = new_invoice
        item.save()
    new_invoice.calculate_totals()
    new_invoice.save()

    messages.success(request, 'فاکتور با موفقیت کپی شد')
    return redirect('frontend:invoice_edit', pk=new_invoice.pk)


@login_required
def invoice_delete_view(request, pk):
    """Delete an invoice (POST only)."""
    if request.method == 'POST':
        invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
        invoice.delete()
        messages.success(request, 'فاکتور با موفقیت حذف شد')
    return redirect('frontend:invoice_list')


@login_required
def invoice_bulk_delete_view(request):
    """Bulk delete invoices (POST only)."""
    if request.method == 'POST':
        ids = request.POST.getlist('invoice_ids')
        if ids:
            deleted = Invoice.objects.filter(id__in=ids, user=request.user).delete()[0]
            messages.success(request, f'{deleted} فاکتور با موفقیت حذف شد')
        else:
            messages.warning(request, 'هیچ فاکتوری انتخاب نشده')
    return redirect('frontend:invoice_list')


# ---------------------------------------------------------------------------
# Customer views
# ---------------------------------------------------------------------------

class CustomerListView(LoginRequiredMixin, ListView):
    """List all customers for the logged-in user."""
    model = Customer
    template_name = 'frontend/customers/list.html'
    context_object_name = 'customers'
    paginate_by = 20

    def get_queryset(self):
        qs = Customer.objects.filter(user=self.request.user)
        q = self.request.GET.get('search', '').strip()
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(phone__icontains=q) |
                Q(national_id__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_query'] = self.request.GET.get('search', '')
        return ctx


class CustomerCreateView(LoginRequiredMixin, View):
    """Create a new customer."""

    def get(self, request):
        return render(request, 'frontend/customers/create.html')

    def post(self, request):
        data = request.POST
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        phone = data.get('phone', '').strip()
        address = data.get('address', '').strip()
        national_id = data.get('national_id', '').strip()

        if not first_name:
            messages.error(request, 'نام مشتری الزامی است')
            return render(request, 'frontend/customers/create.html', {
                'first_name': first_name, 'last_name': last_name,
                'phone': phone, 'address': address, 'national_id': national_id,
            })

        customer = Customer.objects.create(
            user=request.user,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            address=address,
            national_id=national_id,
        )
        messages.success(request, 'مشتری با موفقیت ایجاد شد')
        return redirect('frontend:customer_list')


class CustomerEditView(LoginRequiredMixin, View):
    """Edit an existing customer."""

    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk, user=request.user)
        return render(request, 'frontend/customers/edit.html', {'customer': customer})

    def post(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk, user=request.user)
        data = request.POST
        customer.first_name = data.get('first_name', '').strip()
        customer.last_name = data.get('last_name', '').strip()
        customer.phone = data.get('phone', '').strip()
        customer.address = data.get('address', '').strip()
        customer.national_id = data.get('national_id', '').strip()

        if not customer.first_name:
            messages.error(request, 'نام مشتری الزامی است')
            return render(request, 'frontend/customers/edit.html', {'customer': customer})

        customer.save()
        messages.success(request, 'مشتری با موفقیت به‌روزرسانی شد')
        return redirect('frontend:customer_list')


@login_required
def customer_delete_view(request, pk):
    """Delete a customer (POST only)."""
    if request.method == 'POST':
        customer = get_object_or_404(Customer, pk=pk, user=request.user)
        customer.delete()
        messages.success(request, 'مشتری با موفقیت حذف شد')
    return redirect('frontend:customer_list')


@login_required
def customer_bulk_delete_view(request):
    """Bulk delete customers (POST only)."""
    if request.method == 'POST':
        ids = request.POST.getlist('customer_ids')
        if ids:
            deleted = Customer.objects.filter(id__in=ids, user=request.user).delete()[0]
            messages.success(request, f'{deleted} مشتری با موفقیت حذف شد')
        else:
            messages.warning(request, 'هیچ مشتری انتخاب نشده')
    return redirect('frontend:customer_list')


# ---------------------------------------------------------------------------
# Product views
# ---------------------------------------------------------------------------

class ProductListView(LoginRequiredMixin, ListView):
    """List all products for the logged-in user."""
    model = Product
    template_name = 'frontend/products/list.html'
    context_object_name = 'products'
    paginate_by = 20

    def get_queryset(self):
        qs = Product.objects.filter(user=self.request.user)
        q = self.request.GET.get('search', '').strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(description__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_query'] = self.request.GET.get('search', '')
        return ctx


class ProductCreateView(LoginRequiredMixin, View):
    """Create a new product."""

    def get(self, request):
        return render(request, 'frontend/products/create.html', {
            'frequency_choices': Product.FREQUENCY_CHOICES,
        })

    def post(self, request):
        data = request.POST
        name = data.get('name', '').strip()
        unit = data.get('unit', 'عدد').strip()
        frequency = data.get('frequency', '')
        description = data.get('description', '').strip()
        initial_price = data.get('initial_price', '')

        if not name:
            messages.error(request, 'نام محصول الزامی است')
            return render(request, 'frontend/products/create.html', {
                'frequency_choices': Product.FREQUENCY_CHOICES,
                'name': name, 'unit': unit, 'frequency': frequency,
                'description': description,
            })

        if unit == 'خدمات' and not frequency:
            messages.error(request, 'برای خدمات، انتخاب دوره الزامی است')
            return render(request, 'frontend/products/create.html', {
                'frequency_choices': Product.FREQUENCY_CHOICES,
                'name': name, 'unit': unit, 'frequency': frequency,
                'description': description,
            })

        product = Product.objects.create(
            user=request.user,
            name=name,
            unit=unit,
            frequency=frequency,
            description=description,
        )

        # Optionally set initial price
        if initial_price:
            try:
                price_val = int(float(initial_price))
                if price_val > 0:
                    PriceHistory.objects.create(product=product, price=price_val)
            except (ValueError, TypeError):
                pass

        messages.success(request, 'محصول با موفقیت ایجاد شد')
        return redirect('frontend:product_list')


class ProductEditView(LoginRequiredMixin, View):
    """Edit an existing product."""

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk, user=request.user)
        price_history = product.price_history.all()[:10]
        return render(request, 'frontend/products/edit.html', {
            'product': product,
            'price_history': price_history,
            'frequency_choices': Product.FREQUENCY_CHOICES,
        })

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk, user=request.user)
        data = request.POST
        product.name = data.get('name', '').strip()
        product.unit = data.get('unit', 'عدد').strip()
        product.frequency = data.get('frequency', '')
        product.description = data.get('description', '').strip()

        if not product.name:
            messages.error(request, 'نام محصول الزامی است')
            return render(request, 'frontend/products/edit.html', {
                'product': product,
                'price_history': product.price_history.all()[:10],
                'frequency_choices': Product.FREQUENCY_CHOICES,
            })

        if product.unit == 'خدمات' and not product.frequency:
            messages.error(request, 'برای خدمات، انتخاب دوره الزامی است')
            return render(request, 'frontend/products/edit.html', {
                'product': product,
                'price_history': product.price_history.all()[:10],
                'frequency_choices': Product.FREQUENCY_CHOICES,
            })

        product.save()

        # Handle new price entry
        new_price = data.get('new_price', '')
        if new_price:
            try:
                price_val = int(float(new_price))
                if price_val > 0:
                    PriceHistory.objects.create(product=product, price=price_val)
            except (ValueError, TypeError):
                pass

        messages.success(request, 'محصول با موفقیت به‌روزرسانی شد')
        return redirect('frontend:product_list')


@login_required
def product_delete_view(request, pk):
    """Delete a product (POST only)."""
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=pk, user=request.user)
        product.delete()
        messages.success(request, 'محصول با موفقیت حذف شد')
    return redirect('frontend:product_list')


@login_required
def product_bulk_delete_view(request):
    """Bulk delete products (POST only)."""
    if request.method == 'POST':
        ids = request.POST.getlist('product_ids')
        if ids:
            deleted = Product.objects.filter(id__in=ids, user=request.user).delete()[0]
            messages.success(request, f'{deleted} محصول با موفقیت حذف شد')
        else:
            messages.warning(request, 'هیچ محصولی انتخاب نشده')
    return redirect('frontend:product_list')


# ---------------------------------------------------------------------------
# Bank Account views
# ---------------------------------------------------------------------------

class BankListView(LoginRequiredMixin, ListView):
    """List all bank accounts for the logged-in user."""
    model = BankAccount
    template_name = 'frontend/banks/list.html'
    context_object_name = 'accounts'
    paginate_by = 20

    def get_queryset(self):
        qs = BankAccount.objects.filter(user=self.request.user).select_related('bank')
        q = self.request.GET.get('search', '').strip()
        if q:
            qs = qs.filter(
                Q(bank__name__icontains=q) |
                Q(card_number__icontains=q) |
                Q(iban__icontains=q) |
                Q(account_holder__icontains=q)
            ).distinct()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_query'] = self.request.GET.get('search', '')
        return ctx


class BankCreateView(LoginRequiredMixin, View):
    """Create a new bank account."""

    def get(self, request):
        return render(request, 'frontend/banks/create.html', {
            'form': BankAccountForm(),
            'bank_names': Bank.objects.values_list('name', flat=True),
        })

    def post(self, request):
        form = BankAccountForm(request.POST)
        if form.is_valid():
            bank, _ = Bank.objects.get_or_create(name=form.cleaned_data['bank_name'].strip())
            account = form.save(commit=False)
            account.user = request.user
            account.bank = bank
            account.save()
            messages.success(request, 'حساب بانکی با موفقیت ایجاد شد')
            return redirect('frontend:bank_list')
        return render(request, 'frontend/banks/create.html', {
            'form': form,
            'bank_names': Bank.objects.values_list('name', flat=True),
        })


class BankEditView(LoginRequiredMixin, View):
    """Edit an existing bank account."""

    def get(self, request, pk):
        account = get_object_or_404(BankAccount, pk=pk, user=request.user)
        return render(request, 'frontend/banks/edit.html', {
            'form': BankAccountForm(instance=account),
            'account': account,
            'bank_names': Bank.objects.values_list('name', flat=True),
        })

    def post(self, request, pk):
        account = get_object_or_404(BankAccount, pk=pk, user=request.user)
        form = BankAccountForm(request.POST, instance=account)
        if form.is_valid():
            bank, _ = Bank.objects.get_or_create(name=form.cleaned_data['bank_name'].strip())
            account = form.save(commit=False)
            account.bank = bank
            account.save()
            messages.success(request, 'حساب بانکی با موفقیت به‌روزرسانی شد')
            return redirect('frontend:bank_list')
        return render(request, 'frontend/banks/edit.html', {
            'form': form,
            'account': account,
            'bank_names': Bank.objects.values_list('name', flat=True),
        })


@login_required
def bank_delete_view(request, pk):
    """Delete a bank account (POST only)."""
    if request.method == 'POST':
        account = get_object_or_404(BankAccount, pk=pk, user=request.user)
        account.delete()
        messages.success(request, 'حساب بانکی با موفقیت حذف شد')
    return redirect('frontend:bank_list')


@login_required
def bank_bulk_delete_view(request):
    """Bulk delete bank accounts (POST only)."""
    if request.method == 'POST':
        ids = request.POST.getlist('bank_ids')
        if ids:
            deleted = BankAccount.objects.filter(id__in=ids, user=request.user).delete()[0]
            messages.success(request, f'{deleted} حساب بانکی با موفقیت حذف شد')
        else:
            messages.warning(request, 'هیچ حسابی انتخاب نشده')
    return redirect('frontend:bank_list')


# ---------------------------------------------------------------------------
# Reports views
# ---------------------------------------------------------------------------

@login_required
def reports_view(request):
    """Reports page — sales, customer, and product reports."""
    user = request.user
    report_type = request.GET.get('type', 'sales')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    invoices = Invoice.objects.filter(user=user)
    if date_from:
        invoices = invoices.filter(invoice_date__gte=date_from)
    if date_to:
        invoices = invoices.filter(invoice_date__lte=date_to)

    context = {
        'report_type': report_type,
        'date_from': date_from,
        'date_to': date_to,
        'customers': Customer.objects.filter(user=user).order_by('first_name', 'last_name'),
    }

    if report_type == 'sales':
        # Sales summary
        total_revenue = invoices.aggregate(total=Sum('final_amount'))['total'] or 0
        total_count = invoices.count()
        paid_count = invoices.filter(is_paid=True).count()
        unpaid_count = total_count - paid_count

        # Monthly breakdown
        from django.db.models.functions import TruncMonth
        monthly_sales = (
            invoices
            .annotate(month=TruncMonth('invoice_date'))
            .values('month')
            .annotate(revenue=Sum('final_amount'), count=Count('id'))
            .order_by('-month')
        )[:12]

        # Per-product revenue for the pie chart
        from django.db.models import F, ExpressionWrapper, DecimalField
        product_revenue = list(
            InvoiceItem.objects.filter(invoice__user=user, invoice__in=invoices)
            .values('product_name')
            .annotate(revenue=Sum('total_price'), qty=Sum('quantity'))
            .order_by('-revenue')
        )

        context.update({
            'total_revenue': total_revenue,
            'total_count': total_count,
            'paid_count': paid_count,
            'unpaid_count': unpaid_count,
            'monthly_sales': monthly_sales,
            'product_revenue': product_revenue,
        })

    elif report_type == 'customers':
        # Customer report
        # NOTE: annotation names must NOT collide with Customer model properties
        # (total_purchases / invoice_count are read-only properties — setattr
        # during queryset iteration raises AttributeError).
        customers = (
            Customer.objects.filter(user=user)
            .annotate(
                total_spent=Sum('invoices__final_amount'),
                num_invoices=Count('invoices'),
            )
            .order_by('-total_spent')
        )
        context['customer_stats'] = customers

    elif report_type == 'products':
        # Product report
        products = Product.objects.filter(user=user)
        product_stats = []
        for p in products:
            sold = p.total_sold
            revenue = p.total_revenue
            product_stats.append({
                'product': p,
                'total_sold': sold,
                'total_revenue': revenue,
            })
        product_stats.sort(key=lambda x: x['total_revenue'], reverse=True)
        context['product_stats'] = product_stats

    return render(request, 'frontend/reports.html', context)


# ---------------------------------------------------------------------------
# Settings views
# ---------------------------------------------------------------------------

@login_required
def settings_view(request):
    """User settings — profile, seller info, and password change (with OTP)."""
    from accounts.email_utils import validate_email_strict, create_otp, send_otp_email, verify_otp

    user = request.user
    profile, _ = SellerProfile.objects.get_or_create(user=user)
    PW_KEY = 'pw_change_failures'

    if request.method == 'POST':
        section = request.POST.get('section', '')

        if section == 'profile':
            new_email = request.POST.get('email', '').strip()
            # Validate email if changed
            if new_email and new_email != user.email:
                is_valid, err = validate_email_strict(new_email)
                if not is_valid:
                    messages.error(request, err)
                    return redirect('frontend:settings')
                if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
                    messages.error(request, 'این ایمیل قبلاً ثبت شده است')
                    return redirect('frontend:settings')

            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name = request.POST.get('last_name', '').strip()
            user.email = new_email
            if hasattr(user, 'phone'):
                user.phone = request.POST.get('phone', '').strip()
            user.save()
            messages.success(request, 'پروفایل با موفقیت به‌روزرسانی شد')

        elif section == 'seller':
            profile.business_name = request.POST.get('business_name', '').strip()
            profile.national_id = request.POST.get('national_id', '').strip()
            profile.address = request.POST.get('address', '').strip()
            profile.phone = request.POST.get('seller_phone', '').strip()
            profile.email = request.POST.get('seller_email', '').strip()
            profile.save()
            messages.success(request, 'اطلاعات فروشنده با موفقیت به‌روزرسانی شد')

        elif section == 'password':
            # Check captcha
            captcha_ok, captcha_err = _verify_captcha(request, PW_KEY)
            if not captcha_ok:
                messages.error(request, captcha_err)
                return redirect('frontend:settings')

            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')

            if not user.check_password(current_password):
                _record_failure(request, PW_KEY)
                messages.error(request, 'رمز عبور فعلی اشتباه است')
            elif len(new_password) < 8:
                messages.error(request, 'رمز عبور جدید باید حداقل ۸ کاراکتر باشد')
            elif new_password != confirm_password:
                messages.error(request, 'رمز عبور جدید و تکرار آن مطابقت ندارند')
            else:
                _clear_failures(request, PW_KEY)
                user.set_password(new_password)
                user.save()
                login(request, user)
                messages.success(request, 'رمز عبور با موفقیت تغییر کرد')

        elif section == 'password_otp_request':
            # Send OTP for password change
            if not user.email:
                messages.error(request, 'ابتدا ایمیل خود را در بخش پروفایل ثبت کنید')
            else:
                code = create_otp(user, 'password_change')
                send_otp_email(user, code, 'password_change')
                messages.success(request, 'کد تأیید به ایمیل شما ارسال شد')

        elif section == 'password_otp_change':
            # Verify OTP and change password
            otp_code = request.POST.get('otp_code', '').strip()
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')

            is_valid, err = verify_otp(user, otp_code, 'password_change')
            if not is_valid:
                messages.error(request, err)
            elif len(new_password) < 8:
                messages.error(request, 'رمز عبور جدید باید حداقل ۸ کاراکتر باشد')
            elif new_password != confirm_password:
                messages.error(request, 'رمز عبور جدید و تکرار آن مطابقت ندارند')
            else:
                user.set_password(new_password)
                user.save()
                login(request, user)
                messages.success(request, 'رمز عبور با موفقیت تغییر کرد')

        return redirect('frontend:settings')

    captcha_ctx = _get_captcha_context(request, PW_KEY)
    context = {
        'seller_profile': profile,
        'has_email': bool(user.email),
        'needs_captcha': captcha_ctx['needs_captcha'],
        'captcha_attempts': captcha_ctx['captcha_attempts'],
    }
    return render(request, 'frontend/settings.html', context)


# ---------------------------------------------------------------------------
# API-like endpoints for autocomplete (used by frontend JS)
# ---------------------------------------------------------------------------

@login_required
def customer_autocomplete_view(request):
    """Customer autocomplete endpoint for use by JS in templates."""
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse([], safe=False)

    customers = Customer.objects.filter(
        user=request.user
    ).filter(
        Q(first_name__icontains=q) |
        Q(last_name__icontains=q) |
        Q(phone__icontains=q)
    )[:10]

    results = [
        {
            'id': c.id,
            'full_name': c.full_name,
            'phone': c.phone,
            'address': c.address,
        }
        for c in customers
    ]
    return JsonResponse(results, safe=False)


@login_required
def customer_check_similar(request):
    """Smart customer match: given name + phone, classify against existing customers.

    Returns {status, primary, candidates} — same shape as
    /api/customers/check-match/ so the frontend can reuse modal logic.

    Statuses: exact / phone_conflict / name_conflict / similar / none
    """
    name = request.GET.get('name', '').strip()
    phone = request.GET.get('phone', '').strip()

    if not name and not phone:
        return JsonResponse({'status': 'none', 'primary': None, 'candidates': []})

    from customers.matching import find_customer_match
    result = find_customer_match(request.user, name, phone)
    return JsonResponse(result)


@login_required
def product_autocomplete_view(request):
    """Product autocomplete endpoint for use by JS in templates."""
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse([], safe=False)

    products = Product.objects.filter(
        user=request.user
    ).filter(
        Q(name__icontains=q)
    )[:10]

    results = [
        {
            'id': p.id,
            'name': p.name,
            'unit': p.unit,
            'frequency': p.frequency,
            'price': str(p.latest_price),
        }
        for p in products
    ]
    return JsonResponse(results, safe=False)


@login_required
def bank_account_autocomplete_view(request):
    """Bank account autocomplete — search by bank name, card number, or holder.
    Empty query returns all accounts (for focus dropdown)."""
    q = request.GET.get('q', '').strip()

    qs = BankAccount.objects.filter(user=request.user)
    if q:
        qs = qs.filter(
            Q(bank__name__icontains=q) |
            Q(card_number__icontains=q) |
            Q(account_holder__icontains=q)
        )
    accounts = qs[:10]

    results = [
        {
            'id': a.id,
            'bank_name': a.bank.name,
            'card_number': a.card_number,
            'iban': a.iban,
            'account_holder': a.account_holder,
        }
        for a in accounts
    ]
    return JsonResponse(results, safe=False)


@login_required
def invoice_print_view(request, pk):
    """Print view — renders invoice for printing."""
    invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
    items = invoice.items.all()
    context = {'invoice': invoice, 'items': items}
    return render(request, 'frontend/invoices/print.html', context)


@login_required
def invoice_pdf_view(request, pk):
    """Session-authenticated PDF download — same bytes as /api/pdf/<id>/.

    Used by the save-&-share flow (fetch + Web Share API) where the JWT
    from api.js is not available.
    """
    invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
    from reports.pdf_views import generate_pdf_content
    pdf_bytes = generate_pdf_content(invoice)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{invoice.invoice_number}.pdf"'
    return response


@login_required
def reports_export_view(request):
    """Export sales report as Excel."""
    from reports.export_views import export_excel
    return export_excel(request)


@login_required
def reports_export_customer_pdf_view(request, customer_id):
    """Export PDFs for a specific customer's invoices as a ZIP."""
    from reports.export_views import export_customer_invoices_pdf
    return export_customer_invoices_pdf(request, customer_id)


PREDEFINED_UNITS = ['عدد', 'کیلوگرم', 'گرم', 'لیتر', 'خدمات', 'مسافت']


@login_required
def units_list_view(request):
    """Return all available units (predefined + user custom)."""
    profile, _ = SellerProfile.objects.get_or_create(user=request.user)
    units = PREDEFINED_UNITS + [u for u in profile.custom_units if u not in PREDEFINED_UNITS]
    return JsonResponse(units, safe=False)


@login_required
def unit_add_view(request):
    """Add a custom unit for the logged-in user."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'error': 'نام واحد الزامی است'}, status=400)
    profile, _ = SellerProfile.objects.get_or_create(user=request.user)
    if name not in profile.custom_units:
        profile.custom_units.append(name)
        profile.save(update_fields=['custom_units'])
    units = PREDEFINED_UNITS + [u for u in profile.custom_units if u not in PREDEFINED_UNITS]
    return JsonResponse(units, safe=False)


@login_required
def unit_delete_view(request):
    """Delete a custom unit for the logged-in user."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    name = request.POST.get('name', '').strip()
    profile, _ = SellerProfile.objects.get_or_create(user=request.user)
    if name in profile.custom_units:
        profile.custom_units.remove(name)
        profile.save(update_fields=['custom_units'])
    units = PREDEFINED_UNITS + [u for u in profile.custom_units if u not in PREDEFINED_UNITS]
    return JsonResponse(units, safe=False)
