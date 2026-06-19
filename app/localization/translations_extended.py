"""
Extended localization for Marathi (mr), Tamil (ta), Telugu (te).
Combined with app/localization/translations.py for full 5-language support.
Per spec Section A4.1: minimum English, Hindi, Marathi, Tamil, Telugu.
"""

EXTENDED_TRANSLATIONS: dict[str, dict[str, str]] = {
    "mr": {
        # Common
        "greeting": "प्रिय {name}",
        "regards": "सादर,\nYourBank टीम",
        "ref_id": "संदर्भ आईडी: {ref_id}",

        # Transaction
        "transaction_success_title": "व्यवहार यशस्वी",
        "transaction_success_body": "₹{amount} चा व्यवहार {recipient} ला यशस्वीरित्या पूर्ण झाला.",
        "transaction_failure_title": "व्यवहार अयशस्वी",
        "transaction_failure_body": "₹{amount} चा व्यवहार अयशस्वी. कारण: {reason}.",
        "transaction_pending_title": "व्यवहार प्रक्रियेत",
        "transaction_pending_body": "₹{amount} चा व्यवहार प्रक्रियेत आहे.",
        "transaction_reversed_title": "व्यवहार परत",
        "transaction_reversed_body": "₹{amount} चा व्यवहार परत केला गेला आहे.",

        # Payment
        "payment_due_title": "देयक स्मरण",
        "payment_due_body": "₹{amount} चे देयक {due_date} ला देय आहे.",
        "payment_overdue_title": "देयक थकबाकी",
        "payment_overdue_body": "₹{amount} चे देयक {days} दिवसांपासून थकबाकी आहे.",
        "payment_received_title": "देयक प्राप्त",
        "payment_received_body": "₹{amount} चे देयक प्राप्त झाले. धन्यवाद!",
        "payment_failed_title": "देयक अयशस्वी",
        "payment_failed_body": "₹{amount} चे देयक प्रक्रिया होऊ शकले नाही.",

        # Account
        "account_debit_title": "खात्यातून नावे",
        "account_debit_body": "तुमच्या खात्यातून ₹{amount} नावे झाले. शिल्लक: ₹{balance}.",
        "account_credit_title": "खात्यात जमा",
        "account_credit_body": "तुमच्या खात्यात ₹{amount} जमा झाले. शिल्लक: ₹{balance}.",
        "account_low_balance_title": "कमी शिल्लक सूचना",
        "account_low_balance_body": "तुमची शिल्लक (₹{balance}) किमान आवश्यक (₹{minimum}) पेक्षा कमी आहे.",
        "account_blocked_title": "खाते अवरोधित",
        "account_blocked_body": "तुमचे खाते अवरोधित केले आहे. तात्काळ सहाय्याशी संपर्क करा.",
        "account_statement_title": "विवरण तयार",
        "account_statement_body": "{period} चे खाते विवरण तयार आहे.",

        # Loan
        "loan_approved_title": "कर्ज मंजूर!",
        "loan_approved_body": "तुमचे ₹{amount} चे कर्ज मंजूर झाले! {days} कामाच्या दिवसांत वितरण.",
        "loan_rejected_title": "कर्ज अर्ज नाकारला",
        "loan_rejected_body": "तुमचा कर्ज अर्ज नाकारला गेला. कारण: {reason}.",
        "loan_disbursed_title": "कर्ज वितरित",
        "loan_disbursed_body": "₹{amount} तुमच्या खात्यात वितरित केले गेले आहे.",
        "loan_emi_due_title": "ईएमआय देय स्मरण",
        "loan_emi_due_body": "कर्ज {loan_id} चे ₹{emi_amount} ईएमआय {due_date} ला देय आहे.",
        "loan_emi_missed_title": "ईएमआय चुकला",
        "loan_emi_missed_body": "₹{emi_amount} ईएमआय चुकला. दंड टाळण्यासाठी आत्ता भरा.",

        # Security
        "otp_title": "तुमचा OTP",
        "otp_body": "{otp} हा {purpose} साठी OTP आहे. {validity} मिनिटांसाठी वैध. कुणाशीही शेअर करू नका.",
        "suspicious_activity_title": "सुरक्षा सूचना",
        "suspicious_activity_body": "तुमच्या खात्यावर संशयास्पद क्रियाकलाप आढळला. तात्काळ {helpline} वर कॉल करा.",
        "password_changed_title": "पासवर्ड बदलला",
        "password_changed_body": "तुमचा पासवर्ड बदलला गेला. तुम्ही नाही केले तर तात्काळ सहाय्यास संपर्क करा.",
        "login_detected_title": "नवीन लॉगिन आढळला",
        "login_detected_body": "{device} वरून {location} येथे नवीन लॉगिन. तुम्ही नाही? तुमचे खाते सुरक्षित करा.",

        # KYC
        "kyc_approved_title": "KYC सत्यापित",
        "kyc_approved_body": "तुमचे KYC यशस्वीरित्या सत्यापित झाले. पूर्ण खाते प्रवेश आता उपलब्ध आहे.",
        "kyc_rejected_title": "KYC नाकारले",
        "kyc_rejected_body": "तुमचे KYC नाकारले गेले. कारण: {reason}. कृपया पुन्हा सादर करा.",

        # Welcome & Offers
        "welcome_title": "YourBank मध्ये आपले स्वागत!",
        "welcome_body": "स्वागत आहे, {name}! तुमचे खाते तयार आहे. आमच्या सेवा एक्सप्लोर करा.",
        "offer_available_title": "तुमच्यासाठी विशेष ऑफर!",
        "offer_available_body": "नवीन ऑफर: {offer_description}. {expiry_date} पर्यंत वैध.",
        "offer_expiring_title": "ऑफर लवकरच संपणार!",
        "offer_expiring_body": "तुमचा ऑफर '{offer_description}' {expiry_date} ला संपणार आहे.",

        # Investment
        "investment_matured_title": "गुंतवणूक परिपक्व",
        "investment_matured_body": "₹{amount} ची गुंतवणूक परिपक्व झाली. जमा रक्कम: ₹{maturity_amount}.",
        "investment_dividend_title": "लाभांश जमा",
        "investment_dividend_body": "{scheme} साठी ₹{amount} लाभांश जमा झाला.",
    },

    "ta": {
        # Common
        "greeting": "அன்பான {name}",
        "regards": "மரியாதையுடன்,\nYourBank குழு",
        "ref_id": "குறிப்பு ஐடி: {ref_id}",

        # Transaction
        "transaction_success_title": "பரிவர்த்தனை வெற்றிகரமானது",
        "transaction_success_body": "₹{amount} பரிவர்த்தனை {recipient} க்கு வெற்றிகரமாக முடிந்தது.",
        "transaction_failure_title": "பரிவர்த்தனை தோல்வியடைந்தது",
        "transaction_failure_body": "₹{amount} பரிவர்த்தனை தோல்வியடைந்தது. காரணம்: {reason}.",
        "transaction_pending_title": "பரிவர்த்தனை நடைபெறுகிறது",
        "transaction_pending_body": "₹{amount} பரிவர்த்தனை செயல்பாட்டில் உள்ளது.",
        "transaction_reversed_title": "பரிவர்த்தனை திரும்பப் பெறப்பட்டது",
        "transaction_reversed_body": "₹{amount} பரிவர்த்தனை திரும்பப் பெறப்பட்டது.",

        # Payment
        "payment_due_title": "கட்டணம் நினைவூட்டல்",
        "payment_due_body": "₹{amount} கட்டணம் {due_date} அன்று செலுத்த வேண்டும்.",
        "payment_overdue_title": "கட்டணம் தாமதமானது",
        "payment_overdue_body": "₹{amount} கட்டணம் {days} நாட்கள் தாமதமானது.",
        "payment_received_title": "கட்டணம் பெறப்பட்டது",
        "payment_received_body": "₹{amount} கட்டணம் பெறப்பட்டது. நன்றி!",
        "payment_failed_title": "கட்டணம் தோல்வியடைந்தது",
        "payment_failed_body": "₹{amount} கட்டணம் செயலாக்கப்படவில்லை.",

        # Account
        "account_debit_title": "கணக்கிலிருந்து பற்று",
        "account_debit_body": "உங்கள் கணக்கிலிருந்து ₹{amount} பற்று வைக்கப்பட்டது. இருப்பு: ₹{balance}.",
        "account_credit_title": "கணக்கில் வரவு",
        "account_credit_body": "உங்கள் கணக்கில் ₹{amount} வரவு வைக்கப்பட்டது. இருப்பு: ₹{balance}.",
        "account_low_balance_title": "குறைந்த இருப்பு எச்சரிக்கை",
        "account_low_balance_body": "உங்கள் இருப்பு (₹{balance}) குறைந்தபட்சம் தேவையான (₹{minimum}) விட குறைவாக உள்ளது.",
        "account_blocked_title": "கணக்கு தடுக்கப்பட்டது",
        "account_blocked_body": "உங்கள் கணக்கு தடுக்கப்பட்டது. உடனடியாக ஆதரவை தொடர்பு கொள்ளுங்கள்.",
        "account_statement_title": "அறிக்கை தயார்",
        "account_statement_body": "{period} காலத்திற்கான கணக்கு அறிக்கை தயாராக உள்ளது.",

        # Loan
        "loan_approved_title": "கடன் அனுமதிக்கப்பட்டது!",
        "loan_approved_body": "உங்கள் ₹{amount} கடன் அனுமதிக்கப்பட்டது! {days} வேலை நாட்களில் விடுவிப்பு.",
        "loan_rejected_title": "கடன் விண்ணப்பம் நிராகரிக்கப்பட்டது",
        "loan_rejected_body": "உங்கள் கடன் விண்ணப்பம் நிராகரிக்கப்பட்டது. காரணம்: {reason}.",
        "loan_disbursed_title": "கடன் வழங்கப்பட்டது",
        "loan_disbursed_body": "₹{amount} உங்கள் கணக்கில் வழங்கப்பட்டது.",
        "loan_emi_due_title": "EMI நினைவூட்டல்",
        "loan_emi_due_body": "கடன் {loan_id} க்கான ₹{emi_amount} EMI {due_date} அன்று செலுத்த வேண்டும்.",
        "loan_emi_missed_title": "EMI தவறவிட்டது",
        "loan_emi_missed_body": "₹{emi_amount} EMI தவறவிட்டது. அபராதத்தை தவிர்க்க இப்போது செலுத்துங்கள்.",

        # Security
        "otp_title": "உங்கள் OTP",
        "otp_body": "{otp} என்பது {purpose} க்கான OTP. {validity} நிமிடங்களுக்கு செல்லுபடியாகும். யாரிடமும் பகிரவேண்டாம்.",
        "suspicious_activity_title": "பாதுகாப்பு எச்சரிக்கை",
        "suspicious_activity_body": "உங்கள் கணக்கில் சந்தேகாஸ்பத செயல்பாடு கண்டறியப்பட்டது. உடனடியாக {helpline} ஐ அழைக்கவும்.",
        "password_changed_title": "கடவுச்சொல் மாற்றப்பட்டது",
        "password_changed_body": "உங்கள் கடவுச்சொல் மாற்றப்பட்டது. நீங்கள் செய்யவில்லை என்றால் உடனடியாக ஆதரவை தொடர்பு கொள்ளுங்கள்.",
        "login_detected_title": "புதிய உள்நுழைவு கண்டறியப்பட்டது",
        "login_detected_body": "{device} இலிருந்து {location} இல் புதிய உள்நுழைவு. நீங்கள் இல்லையா? உங்கள் கணக்கை பாதுகாக்கவும்.",

        # KYC
        "kyc_approved_title": "KYC சரிபார்க்கப்பட்டது",
        "kyc_approved_body": "உங்கள் KYC வெற்றிகரமாக சரிபார்க்கப்பட்டது. முழு கணக்கு அணுகல் இப்போது கிடைக்கிறது.",
        "kyc_rejected_title": "KYC நிராகரிக்கப்பட்டது",
        "kyc_rejected_body": "உங்கள் KYC நிராகரிக்கப்பட்டது. காரணம்: {reason}. மீண்டும் சமர்ப்பிக்கவும்.",

        # Welcome & Offers
        "welcome_title": "YourBank க்கு வரவேற்கிறோம்!",
        "welcome_body": "வரவேற்கிறோம், {name}! உங்கள் கணக்கு தயாராக உள்ளது.",
        "offer_available_title": "உங்களுக்கான சிறப்பு சலுகை!",
        "offer_available_body": "புதிய சலுகை: {offer_description}. {expiry_date} வரை செல்லுபடியாகும்.",
        "offer_expiring_title": "சலுகை விரைவில் முடியும்!",
        "offer_expiring_body": "உங்கள் சலுகை '{offer_description}' {expiry_date} அன்று முடியும்.",

        # Investment
        "investment_matured_title": "முதலீடு முதிர்ந்தது",
        "investment_matured_body": "₹{amount} முதலீடு முதிர்ந்தது. வரவு தொகை: ₹{maturity_amount}.",
        "investment_dividend_title": "ஈவுத்தொகை வரவு",
        "investment_dividend_body": "{scheme} க்கான ₹{amount} ஈவுத்தொகை வரவு வைக்கப்பட்டது.",
    },

    "te": {
        # Common
        "greeting": "ప్రియమైన {name}",
        "regards": "గౌరవంగా,\nYourBank బృందం",
        "ref_id": "సూచన ID: {ref_id}",

        # Transaction
        "transaction_success_title": "లావాదేవీ విజయవంతమైంది",
        "transaction_success_body": "₹{amount} లావాదేవీ {recipient} కి విజయవంతంగా పూర్తయింది.",
        "transaction_failure_title": "లావాదేవీ విఫలమైంది",
        "transaction_failure_body": "₹{amount} లావాదేవీ విఫలమైంది. కారణం: {reason}.",
        "transaction_pending_title": "లావాదేవీ ప్రాసెస్ అవుతోంది",
        "transaction_pending_body": "₹{amount} లావాదేవీ ప్రాసెస్ అవుతోంది.",
        "transaction_reversed_title": "లావాదేవీ రివర్స్ అయింది",
        "transaction_reversed_body": "₹{amount} లావాదేవీ రివర్స్ చేయబడింది.",

        # Payment
        "payment_due_title": "చెల్లింపు రిమైండర్",
        "payment_due_body": "₹{amount} చెల్లింపు {due_date} న చెల్లించాలి.",
        "payment_overdue_title": "చెల్లింపు ఆలస్యమైంది",
        "payment_overdue_body": "₹{amount} చెల్లింపు {days} రోజులుగా ఆలస్యమైంది.",
        "payment_received_title": "చెల్లింపు అందుకున్నారు",
        "payment_received_body": "₹{amount} చెల్లింపు అందుకున్నారు. ధన్యవాదాలు!",
        "payment_failed_title": "చెల్లింపు విఫలమైంది",
        "payment_failed_body": "₹{amount} చెల్లింపు ప్రాసెస్ చేయలేదు.",

        # Account
        "account_debit_title": "అకౌంట్ నుండి డెబిట్",
        "account_debit_body": "మీ అకౌంట్ నుండి ₹{amount} డెబిట్ అయింది. బ్యాలెన్స్: ₹{balance}.",
        "account_credit_title": "అకౌంట్ లో క్రెడిట్",
        "account_credit_body": "మీ అకౌంట్ లో ₹{amount} క్రెడిట్ అయింది. బ్యాలెన్స్: ₹{balance}.",
        "account_low_balance_title": "తక్కువ బ్యాలెన్స్ హెచ్చరిక",
        "account_low_balance_body": "మీ బ్యాలెన్స్ (₹{balance}) కనీస అవసరమైన (₹{minimum}) కంటే తక్కువగా ఉంది.",
        "account_blocked_title": "అకౌంట్ బ్లాక్ అయింది",
        "account_blocked_body": "మీ అకౌంట్ బ్లాక్ అయింది. వెంటనే సపోర్ట్ సంప్రదించండి.",
        "account_statement_title": "స్టేట్‌మెంట్ సిద్ధంగా ఉంది",
        "account_statement_body": "{period} కాలానికి అకౌంట్ స్టేట్‌మెంట్ సిద్ధంగా ఉంది.",

        # Loan
        "loan_approved_title": "రుణం ఆమోదించబడింది!",
        "loan_approved_body": "మీ ₹{amount} రుణం ఆమోదించబడింది! {days} పని దినాలలో విడుదల.",
        "loan_rejected_title": "రుణ దరఖాస్తు తిరస్కరించబడింది",
        "loan_rejected_body": "మీ రుణ దరఖాస్తు తిరస్కరించబడింది. కారణం: {reason}.",
        "loan_disbursed_title": "రుణం విడుదల అయింది",
        "loan_disbursed_body": "₹{amount} మీ అకౌంట్ లో జమ చేయబడింది.",
        "loan_emi_due_title": "EMI రిమైండర్",
        "loan_emi_due_body": "రుణం {loan_id} కు ₹{emi_amount} EMI {due_date} న చెల్లించాలి.",
        "loan_emi_missed_title": "EMI మిస్సయింది",
        "loan_emi_missed_body": "₹{emi_amount} EMI మిస్సయింది. పెనాల్టీ నివారించడానికి ఇప్పుడే చెల్లించండి.",

        # Security
        "otp_title": "మీ OTP",
        "otp_body": "{otp} అనేది {purpose} కోసం OTP. {validity} నిమిషాలు వరకు చెల్లుతుంది. ఎవరికీ చెప్పవద్దు.",
        "suspicious_activity_title": "భద్రతా హెచ్చరిక",
        "suspicious_activity_body": "మీ అకౌంట్ లో అనుమానాస్పద కార్యకలాపం గుర్తించబడింది. వెంటనే {helpline} కి కాల్ చేయండి.",
        "password_changed_title": "పాస్‌వర్డ్ మార్చబడింది",
        "password_changed_body": "మీ పాస్‌వర్డ్ మార్చబడింది. మీరు చేయలేదంటే వెంటనే సపోర్ట్ సంప్రదించండి.",
        "login_detected_title": "కొత్త లాగిన్ గుర్తించబడింది",
        "login_detected_body": "{device} నుండి {location} లో కొత్త లాగిన్. మీరు కాదా? మీ అకౌంట్ ని సురక్షితపరచండి.",

        # KYC
        "kyc_approved_title": "KYC ధృవీకరించబడింది",
        "kyc_approved_body": "మీ KYC విజయవంతంగా ధృవీకరించబడింది. పూర్తి అకౌంట్ యాక్సెస్ ఇప్పుడు అందుబాటులో ఉంది.",
        "kyc_rejected_title": "KYC తిరస్కరించబడింది",
        "kyc_rejected_body": "మీ KYC తిరస్కరించబడింది. కారణం: {reason}. దయచేసి మళ్లీ సమర్పించండి.",

        # Welcome & Offers
        "welcome_title": "YourBank కి స్వాగతం!",
        "welcome_body": "స్వాగతం, {name}! మీ అకౌంట్ సిద్ధంగా ఉంది. మా సేవలను అన్వేషించండి.",
        "offer_available_title": "మీకోసం ప్రత్యేక ఆఫర్!",
        "offer_available_body": "కొత్త ఆఫర్: {offer_description}. {expiry_date} వరకు చెల్లుతుంది.",
        "offer_expiring_title": "ఆఫర్ త్వరలో ముగుస్తోంది!",
        "offer_expiring_body": "మీ ఆఫర్ '{offer_description}' {expiry_date} న ముగుస్తుంది.",

        # Investment
        "investment_matured_title": "పెట్టుబడి మెచ్యూర్ అయింది",
        "investment_matured_body": "₹{amount} పెట్టుబడి మెచ్యూర్ అయింది. క్రెడిట్ అమౌంట్: ₹{maturity_amount}.",
        "investment_dividend_title": "డివిడెండ్ క్రెడిట్",
        "investment_dividend_body": "{scheme} కోసం ₹{amount} డివిడెండ్ క్రెడిట్ అయింది.",
    },
}
