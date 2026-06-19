from typing import Any, Dict, Optional

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # Common
        "greeting": "Dear {name}",
        "regards": "Regards,\nYourBank Team",
        "contact_support": "Contact support at {helpline}",
        "ref_id": "Reference ID: {ref_id}",

        # Transaction
        "transaction_success_title": "Transaction Successful",
        "transaction_success_body": "Your transaction of ₹{amount} to {recipient} was successful.",
        "transaction_failure_title": "Transaction Failed",
        "transaction_failure_body": "Your transaction of ₹{amount} failed. Reason: {reason}.",
        "transaction_pending_title": "Transaction Pending",
        "transaction_pending_body": "Your transaction of ₹{amount} is being processed.",
        "transaction_reversed_title": "Transaction Reversed",
        "transaction_reversed_body": "Your transaction of ₹{amount} has been reversed.",

        # Payment
        "payment_due_title": "Payment Due Reminder",
        "payment_due_body": "Payment of ₹{amount} is due on {due_date}.",
        "payment_overdue_title": "Payment Overdue",
        "payment_overdue_body": "Your payment of ₹{amount} is overdue by {days} days.",
        "payment_received_title": "Payment Received",
        "payment_received_body": "We received your payment of ₹{amount}. Thank you!",
        "payment_failed_title": "Payment Failed",
        "payment_failed_body": "Your payment of ₹{amount} could not be processed.",

        # Account
        "account_debit_title": "Account Debited",
        "account_debit_body": "₹{amount} debited from your account. Balance: ₹{balance}.",
        "account_credit_title": "Account Credited",
        "account_credit_body": "₹{amount} credited to your account. Balance: ₹{balance}.",
        "account_low_balance_title": "Low Balance Alert",
        "account_low_balance_body": "Your balance (₹{balance}) is below the minimum required (₹{minimum}).",
        "account_blocked_title": "Account Blocked",
        "account_blocked_body": "Your account has been blocked. Contact support immediately.",
        "account_statement_title": "Statement Ready",
        "account_statement_body": "Your account statement for {period} is ready.",

        # Loan
        "loan_approved_title": "Loan Approved!",
        "loan_approved_body": "Your loan of ₹{amount} has been approved! Disbursement in {days} working days.",
        "loan_rejected_title": "Loan Application Rejected",
        "loan_rejected_body": "Your loan application was rejected. Reason: {reason}.",
        "loan_disbursed_title": "Loan Disbursed",
        "loan_disbursed_body": "₹{amount} has been disbursed to your account.",
        "loan_emi_due_title": "EMI Due Reminder",
        "loan_emi_due_body": "EMI of ₹{emi_amount} for loan {loan_id} is due on {due_date}.",
        "loan_emi_missed_title": "EMI Missed",
        "loan_emi_missed_body": "Your EMI of ₹{emi_amount} was missed. Pay now to avoid penalties.",

        # Security
        "otp_title": "Your OTP",
        "otp_body": "{otp} is your OTP for {purpose}. Valid for {validity} minutes. Do NOT share.",
        "suspicious_activity_title": "Security Alert",
        "suspicious_activity_body": "Suspicious activity detected on your account. Call {helpline} immediately.",
        "password_changed_title": "Password Changed",
        "password_changed_body": "Your password was changed. If not you, contact support immediately.",
        "login_detected_title": "New Login Detected",
        "login_detected_body": "New login from {device} at {location}. Not you? Secure your account.",

        # KYC
        "kyc_approved_title": "KYC Verified",
        "kyc_approved_body": "Your KYC has been verified successfully. Full account access is now available.",
        "kyc_rejected_title": "KYC Rejected",
        "kyc_rejected_body": "Your KYC was rejected. Reason: {reason}. Please resubmit.",

        # Investment
        "investment_matured_title": "Investment Matured",
        "investment_matured_body": "Your investment of ₹{amount} has matured. Amount credited: ₹{maturity_amount}.",
        "investment_dividend_title": "Dividend Credited",
        "investment_dividend_body": "Dividend of ₹{amount} for {scheme} has been credited.",

        # Welcome
        "welcome_title": "Welcome to YourBank!",
        "welcome_body": "Welcome, {name}! Your account is ready. Start exploring our services.",

        # Offer
        "offer_available_title": "Exclusive Offer for You!",
        "offer_available_body": "You have a new offer: {offer_description}. Valid till {expiry_date}.",
        "offer_expiring_title": "Offer Expiring Soon!",
        "offer_expiring_body": "Your offer '{offer_description}' expires on {expiry_date}. Avail now!",
    },
    "hi": {
        # Common
        "greeting": "प्रिय {name}",
        "regards": "सादर,\nYourBank टीम",
        "contact_support": "सहायता के लिए {helpline} पर संपर्क करें",
        "ref_id": "संदर्भ आईडी: {ref_id}",

        # Transaction
        "transaction_success_title": "लेनदेन सफल",
        "transaction_success_body": "₹{amount} का लेनदेन {recipient} को सफलतापूर्वक पूरा हुआ।",
        "transaction_failure_title": "लेनदेन विफल",
        "transaction_failure_body": "₹{amount} का लेनदेन विफल रहा। कारण: {reason}।",
        "transaction_pending_title": "लेनदेन प्रक्रियाधीन",
        "transaction_pending_body": "₹{amount} का लेनदेन प्रक्रिया में है।",
        "transaction_reversed_title": "लेनदेन वापस",
        "transaction_reversed_body": "₹{amount} का लेनदेन वापस कर दिया गया है।",

        # Payment
        "payment_due_title": "भुगतान देय अनुस्मारक",
        "payment_due_body": "₹{amount} का भुगतान {due_date} को देय है।",
        "payment_overdue_title": "भुगतान अतिदेय",
        "payment_overdue_body": "₹{amount} का भुगतान {days} दिन से अतिदेय है।",
        "payment_received_title": "भुगतान प्राप्त",
        "payment_received_body": "₹{amount} का भुगतान प्राप्त हुआ। धन्यवाद!",
        "payment_failed_title": "भुगतान विफल",
        "payment_failed_body": "₹{amount} का भुगतान संसाधित नहीं हो सका।",

        # Account
        "account_debit_title": "खाते से डेबिट",
        "account_debit_body": "आपके खाते से ₹{amount} डेबिट हुआ। शेष: ₹{balance}।",
        "account_credit_title": "खाते में क्रेडिट",
        "account_credit_body": "आपके खाते में ₹{amount} क्रेडिट हुआ। शेष: ₹{balance}।",
        "account_low_balance_title": "कम शेष राशि चेतावनी",
        "account_low_balance_body": "आपकी शेष राशि (₹{balance}) न्यूनतम आवश्यक (₹{minimum}) से कम है।",
        "account_blocked_title": "खाता अवरुद्ध",
        "account_blocked_body": "आपका खाता अवरुद्ध कर दिया गया है। तुरंत सहायता से संपर्क करें।",
        "account_statement_title": "विवरण तैयार",
        "account_statement_body": "{period} का खाता विवरण तैयार है।",

        # Loan
        "loan_approved_title": "ऋण स्वीकृत!",
        "loan_approved_body": "आपका ₹{amount} का ऋण स्वीकृत हो गया! {days} कार्य दिवसों में वितरण।",
        "loan_rejected_title": "ऋण आवेदन अस्वीकृत",
        "loan_rejected_body": "आपका ऋण आवेदन अस्वीकृत हुआ। कारण: {reason}।",
        "loan_disbursed_title": "ऋण वितरित",
        "loan_disbursed_body": "₹{amount} आपके खाते में वितरित किया गया है।",
        "loan_emi_due_title": "ईएमआई देय अनुस्मारक",
        "loan_emi_due_body": "ऋण {loan_id} की ₹{emi_amount} की ईएमआई {due_date} को देय है।",
        "loan_emi_missed_title": "ईएमआई छूट गई",
        "loan_emi_missed_body": "₹{emi_amount} की ईएमआई छूट गई। जुर्माने से बचने के लिए अभी भुगतान करें।",

        # Security
        "otp_title": "आपका ओटीपी",
        "otp_body": "{otp} आपका {purpose} के लिए ओटीपी है। {validity} मिनट के लिए वैध। किसी से साझा न करें।",
        "suspicious_activity_title": "सुरक्षा चेतावनी",
        "suspicious_activity_body": "आपके खाते पर संदिग्ध गतिविधि का पता चला। तुरंत {helpline} पर कॉल करें।",
        "password_changed_title": "पासवर्ड बदला गया",
        "password_changed_body": "आपका पासवर्ड बदल दिया गया। यदि आपने नहीं किया, तो तुरंत सहायता से संपर्क करें।",
        "login_detected_title": "नया लॉगिन पता चला",
        "login_detected_body": "{device} से {location} पर नया लॉगिन। आप नहीं हैं? अपना खाता सुरक्षित करें।",

        # KYC
        "kyc_approved_title": "केवाईसी सत्यापित",
        "kyc_approved_body": "आपका केवाईसी सफलतापूर्वक सत्यापित हो गया। पूर्ण खाता पहुंच अब उपलब्ध है।",
        "kyc_rejected_title": "केवाईसी अस्वीकृत",
        "kyc_rejected_body": "आपका केवाईसी अस्वीकृत हुआ। कारण: {reason}। कृपया पुनः जमा करें।",

        # Investment
        "investment_matured_title": "निवेश परिपक्व",
        "investment_matured_body": "₹{amount} का आपका निवेश परिपक्व हो गया। क्रेडिट राशि: ₹{maturity_amount}।",
        "investment_dividend_title": "लाभांश क्रेडिट",
        "investment_dividend_body": "{scheme} के लिए ₹{amount} का लाभांश क्रेडिट हुआ।",

        # Welcome
        "welcome_title": "YourBank में आपका स्वागत है!",
        "welcome_body": "स्वागत है, {name}! आपका खाता तैयार है। हमारी सेवाएं एक्सप्लोर करें।",

        # Offer
        "offer_available_title": "आपके लिए विशेष ऑफर!",
        "offer_available_body": "आपके लिए नया ऑफर: {offer_description}। {expiry_date} तक वैध।",
        "offer_expiring_title": "ऑफर जल्द समाप्त होगा!",
        "offer_expiring_body": "आपका ऑफर '{offer_description}' {expiry_date} को समाप्त होगा। अभी लाभ उठाएं!",
    },
}


def _build_full_translations() -> dict[str, dict[str, str]]:
    from app.localization.translations_extended import EXTENDED_TRANSLATIONS
    merged = dict(TRANSLATIONS)
    for locale, strings in EXTENDED_TRANSLATIONS.items():
        merged[locale] = strings
    return merged


_ALL_TRANSLATIONS: dict[str, dict[str, str]] | None = None


def _get_all() -> dict[str, dict[str, str]]:
    global _ALL_TRANSLATIONS
    if _ALL_TRANSLATIONS is None:
        _ALL_TRANSLATIONS = _build_full_translations()
    return _ALL_TRANSLATIONS


def translate(key: str, locale: str = "en", **kwargs: Any) -> str:
    all_t = _get_all()
    lang = all_t.get(locale, all_t["en"])
    template = lang.get(key, all_t["en"].get(key, key))
    try:
        return template.format(**kwargs)
    except (KeyError, ValueError):
        return template


def get_supported_locales() -> list[str]:
    return list(_get_all().keys())
