from fastapi import FastAPI, HTTPException, Header, APIRouter, Request
from fastapi.responses import JSONResponse
from app.config.db import collection_point_collection, developer_details_collection
from bson import ObjectId
from datetime import datetime
import secrets
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from limits.storage import RedisStorage

noticeRouter = APIRouter()

# Initialize RedisStorage and Limiter
redis_url = "redis://localhost:6379/0"  # Adjust the Redis URL as needed
storage = RedisStorage(redis_url)
limiter = Limiter(key_func=get_remote_address, storage_uri=redis_url)


@noticeRouter.get("/get-notice-info", tags=["Notice Info"])
@limiter.limit("5/minute")
async def get_notice_info(
    request: Request,
    cp_id: str = Header(...),
    app_id: str = Header(...),
    org_id: str = Header(...),
    org_key: str = Header(...),
    org_secret: str = Header(...),
):
    organisation = developer_details_collection.find_one(
        {"organisation_id": org_id, "org_key": org_key, "org_secret": org_secret}
    )
    if not organisation:
        raise HTTPException(status_code=401, detail="Invalid org_key or org_secret")

    collection_point = collection_point_collection.find_one(
        {"_id": ObjectId(cp_id), "org_id": org_id, "application_id": app_id}
    )

    if not collection_point:
        raise HTTPException(
            status_code=404, detail=f"Collection point with ID {cp_id} not found"
        )

    notice_info = {
        "urls": {
            "logo": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTI2K4cwj_yTWk-rSebFdFF-tX1yMKE8o_Uwnk5H9GYkIoqSKHAvt-pYaB1dEQHK1paNNk&usqp=CAU",
            "speakIcon": "https://www.svgrepo.com/show/165176/speaking.svg",
            "pauseIcon": "https://www.svgrepo.com/show/149256/pause-button.svg",
            "arrowIcon": "https://cdn.icon-icons.com/icons2/2248/PNG/512/arrow_top_right_icon_135926.png",
            "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
            "dpar_link": "https://www.instagram.com",
            "manage_consent_link": "https://www.facebook.com",
        },
        "english": {
            "collection_point": {},
            "meta_data": {
                "header": "Consent Notice",
                "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "title": "Digital Personal Data Protection Act 2023",
                "description": "An Act to provide for the processing of digital personal data in a manner that recognises both the right of individuals to protect their personal data and the need to process such personal data for lawful purposes and for matters connected therewith or incidental thereto",
                "manage_consent_title": "Manage Consent Preferences",
            },
            "button": {
                "primary": "Accept",
                "secondary": "Cancel",
                "selectAll": "Select All",
            },
        },
        "hindi": {
            "collection_point": {},
            "meta_data": {
                "header": "डेटा सहमति सूचना",
                "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "title": "डिजिटल व्यक्तिगत डेटा संरक्षण अधिनियम 2023",
                "description": "डिजिटल व्यक्तिगत डेटा के प्रसंस्करण के लिए इस तरह से प्रावधान करने के लिए एक अधिनियम जो व्यक्तियों के अपने व्यक्तिगत डेटा की सुरक्षा के अधिकार और कानूनी उद्देश्यों के लिए ऐसे व्यक्तिगत डेटा को संसाधित करने की आवश्यकता और उससे जुड़े या उसके प्रासंगिक मामलों को मान्यता देता है।",
                "manage_consent_title": "सहमति प्राथमिकताएँ प्रबंधित करें",
            },
            "button": {
                "primary": "स्वीकार",
                "secondary": "रद्द",
                "selectAll": "सबका चयन करें",
            },
        },
        "tamil": {
            "collection_point": {},
            "meta_data": {
                "header": "ஒப்புதல் அறிவிப்பு",
                "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "title": "டிஜிட்டல் தனிப்பட்ட தரவுகளை பாதுகாப்பு சட்டம் 2023",
                "description": "நபர்களின் தனிப்பட்ட தரவுகளை பாதுகாக்கும் உரிமையை மற்றும் சட்டப்பூர்வமான நோக்கங்களுக்காக அவ்வாறு தனிப்பட்ட தரவுகளை செயலாக்கும் தேவையை கௌரவிக்கும் வகையில் டிஜிட்டல் தனிப்பட்ட தரவுகளை செயலாக்குவதற்கான ஒரு சட்டம் மற்றும் அதனுடன் தொடர்புடைய அல்லது உச்சிகாவியவற்றை சார்ந்த விவகாரங்களுக்கான ஒரு சட்டம்",
                "manage_consent_title": "ஒப்புதல் முன்னுரிமைகளை நிர்வகிக்கவும்",
            },
            "button": {
                "primary": "ஏற்றுக்கொள்",
                "secondary": "ரத்து",
                "selectAll": "அனைத்தையும் தேர்வுசெய்க",
            },
        },
        "telugu": {
            "collection_point": {},
            "meta_data": {
                "header": "సమ్మతి నోటీసు",
                "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "title": "డిజిటల్ వ్యక్తిగత డేటా రక్షణ చట్టం 2023",
                "description": "వ్యక్తుల వ్యక్తిగత డేటా రక్షణ హక్కును మరియు చట్టబద్ధమైన ఉద్దేశ్యాల కోసం ఆ డేటాను ప్రాసెస్ చేయడానికి అవసరాన్ని గుర్తించేవిధంగా డిజిటల్ వ్యక్తిగత డేటా ప్రాసెసింగ్ కోసం ఒక చట్టం మరియు దానికి సంబంధించిన లేదా అనుబంధ విషయాల కోసం",
                "manage_consent_title": "సమ్మతి ప్రాధాన్యతలను నిర్వహించండి",
            },
            "button": {
                "primary": "అంగీకరించు",
                "secondary": "రద్దు చేయి",
                "selectAll": "అన్నీ ఎంచుకో",
            },
        },
        "gujarati": {
            "collection_point": {},
            "meta_data": {
                "header": "મંજુરી સૂચના",
                "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "title": "ડિજિટલ વ્યક્તિગત ડેટા સુરક્ષા અધિનિયમ 2023",
                "description": "વ્યક્તિઓના વ્યક્તિગત ડેટાને સુરક્ષિત રાખવા હક્ક અને કાનૂની હેતુઓ માટે આવા ડેટાના પ્રોસેસિંગની જરૂરિયાત બંનેને માન્યતા આપતી રીતે ડિજિટલ વ્યક્તિગત ડેટાના પ્રોસેસિંગ માટેનો એક અધિનિયમ અને તેનાથી જોડાયેલા અથવા સબંધિત બાબતો માટે",
                "manage_consent_title": "મંજુરી પસંદગીઓ મેનેજ કરો",
            },
            "button": {
                "primary": "સ્વીકારો",
                "secondary": "રદ કરો",
                "selectAll": "બધા પસંદ કરો",
            },
        },
        "assamese": {
            "collection_point": {},
            "meta_data": {
                "header": "সম্মতি সূচনা",
                "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "title": "ডিজিটেল ব্যক্তিগত তথ্য সুৰক্ষা আইন 2023",
                "description": "ব্যক্তিৰ ব্যক্তিগত তথ্য সুৰক্ষাৰ অধিকাৰ আৰু আইনানুগ উদ্দেশ্যৰ বাবে সেই ব্যক্তিগত তথ্য প্ৰসেশন কৰিবলৈ প্ৰয়োজনীয়তাক মান্যতা দিয়াৰ কাৰণে ডিজিটেল ব্যক্তিগত তথ্য প্ৰসেশনৰ ব্যৱস্থা কৰিবলৈ এক আইন আৰু তাৰ সৈতে সম্পৰ্কিত বা আনুষঙ্গিক বিষয়ৰ বাবে এক আইন",
                "manage_consent_title": "সম্মতি পছন্দসমূহ পৰিচালনা কৰক",
            },
            "button": {
                "primary": "গ্ৰহণ কৰক",
                "secondary": "বাতিল কৰক",
                "selectAll": "সকলো বাছক",
            },
        },
        "bengali": {
            "collection_point": {},
            "meta_data": {
                "header": "সম্মতি নোটিশ",
                "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "title": "ডিজিটাল ব্যক্তিগত তথ্য সুরক্ষা আইন 2023",
                "description": "একটি আইন যা ব্যক্তিরা তাদের ব্যক্তিগত তথ্য সুরক্ষার অধিকার এবং এই ধরনের ব্যক্তিগত তথ্য আইনগত উদ্দেশ্যে প্রক্রিয়া করার প্রয়োজনীয়তা উভয়কেই স্বীকৃতি দেয়, ডিজিটাল ব্যক্তিগত তথ্য প্রক্রিয়া করার জন্য এবং এর সাথে সম্পর্কিত বা আনুষঙ্গিক বিষয়ে একটি আইন",
                "manage_consent_title": "সম্মতি পছন্দগুলি পরিচালনা করুন",
            },
            "button": {
                "primary": "গ্রহণ করুন",
                "secondary": "বাতিল করুন",
                "selectAll": "সবগুলি নির্বাচন করুন",
            },
        },
        "bodo": {
            "collection_point": {},
            "meta_data": {
                "header": "अनुमति बिजेनाय",
                "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "title": "डिजिटल व्यक्तिगत डेटा रक्षा ऐन 2023",
                "description": "दखालोंगुं आपन व्यक्तिगत डेटा सुरुखो अरथ बिसारवाव अर कानूनी उद्देश्य नाय दादखाल किया होओ बिसारवाव ददरखाय माने ओसोर डाटानाय प्रोससिंग करव फालंगुं बिसार होओ एक ऐन अर हेगोगोनाय संबधि ओसोर या उडातै बिजें नाय एक ऐन",
                "manage_consent_title": "अनुमति प्रायोरिटिज मोजैनाव",
            },
            "button": {
                "primary": "आसरा",
                "secondary": "खतमाव",
                "selectAll": "सब ओनाय चुनाव",
            },
        },
        "dogri": {
            "collection_point": {},
            "meta_data": {
                "header": "सहमति सूचना",
                "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "title": "डिजिटल व्यक्तिगत डेटा संरक्षण अधिनियम 2023",
                "description": "डिजिटल व्यक्तिगत डेटा दे प्रोसेसिंग दे लई इक क़ानून जो की व्यक्तियों दे व्यक्तिगत डेटा दे संरक्षण दे अधिकार अते ऐसे व्यक्तिगत डेटा नू क़ानूनी मकसदां दे लई प्रोसेस करन दी लोड नू मान्यता दिन्दा है, अते उसनाल जुड़े होए या उस दे होर मामले लई",
                "manage_consent_title": "सहमति प्राथमिकतावाँ प्रबंधित करो",
            },
            "button": {
                "primary": "स्वीकारो",
                "secondary": "रद्द करो",
                "selectAll": "सारे चूनो",
            },
        },
        "kashmiri": {
            "collection_point": {},
            "meta_data": {
                "header": "رضایت نامہ",
                "mp3Link": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "title": "ڈیجیٹل پرسنل ڈیٹا پروٹیکشن ایکٹ 2023",
                "description": "ایک ایسا قانون جو افراد کے ذاتی ڈیٹا کے تحفظ کے حق اور اس طرح کے ذاتی ڈیٹا کو قانونی مقاصد کے لیے پروسیس کرنے کی ضرورت دونوں کو تسلیم کرتا ہے، ڈیجیٹل ذاتی ڈیٹا پروسیسنگ کے لیے اور اس سے متعلقہ یا اس سے متعلق معاملات کے لیے",
                "manage_consent_title": "رضامندی کی ترجیحات کا نظم کریں",
            },
            "button": {
                "primary": "قبول کریں",
                "secondary": "منسوخ کریں",
                "selectAll": "سبھی کا انتخاب کریں",
            },
        },
    }

    data_elements = []
    for de in collection_point.get("data_elements", []):
        purposes = []
        for purpose in de.get("purposes", []):
            purposes.append(
                {
                    "purpose_id": purpose.get("purpose_id", ""),
                    "purpose_description": purpose.get("purpose_description", ""),
                    "purpose_language": purpose.get("purpose_language", ""),
                }
            )
        data_elements.append(
            {
                "data_element": de.get("data_element", ""),
                "data_element_title": de.get("data_element_title", ""),
                "data_element_description": de.get("data_element_description", ""),
                "data_owner": de.get("data_owner", ""),
                "legal_basis": de.get("legal_basis", ""),
                "retention_period": de.get("retention_period", ""),
                "cross_border": de.get("cross_border", False),
                "sensitive": de.get("sensitive", False),
                "encrypted": de.get("encrypted", False),
                "expiry": de.get("expiry", ""),
                "purposes": purposes,
            }
        )

    collection_point_info = {
        "cp_id": str(collection_point["_id"]),
        "cp_name": collection_point.get("cp_name", ""),
        "cp_status": collection_point.get("cp_status", ""),
        "cp_url": collection_point.get("cp_url", ""),
        "data_elements": data_elements,
    }

    notice_info["english"]["collection_point"] = collection_point_info
    notice_info["hindi"]["collection_point"] = collection_point_info
    notice_info["tamil"]["collection_point"] = collection_point_info
    notice_info["telugu"]["collection_point"] = collection_point_info
    notice_info["gujarati"]["collection_point"] = collection_point_info
    notice_info["assamese"]["collection_point"] = collection_point_info
    notice_info["bengali"]["collection_point"] = collection_point_info
    notice_info["bodo"]["collection_point"] = collection_point_info
    notice_info["dogri"]["collection_point"] = collection_point_info
    notice_info["kashmiri"]["collection_point"] = collection_point_info

    return {"notice_info": notice_info}
