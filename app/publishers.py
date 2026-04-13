"""Publisher lists and batch rotation logic."""

from __future__ import annotations

P0_PUBLISHERS: list[str] = [
    "employers.io", "Joblift", "JobGet", "Snagajob", "Jobcase",
    "Monster", "Allthetopbananas", "JobRapido", "Talent.com", "Talroo",
    "ZipRecruiter", "OnTimeHire", "Indeed", "Sercanto", "YadaJobs",
    "Hokify", "Upward.net", "JobCloud", "Jooble", "Nurse.com",
    "Geographic Solutions", "Reed", "Jobbsafari.se", "Jobbland",
    "Handshake", "1840",
]

P1_P2_PUBLISHERS: list[str] = [
    "JobSwipe", "Jobbird.de", "Tideri", "Manymore.jobs", "ClickaJobs",
    "MyJobScanner", "Job Traffic", "Jobtome", "Propel", "AllJobs",
    "Jora", "EarnBetter", "WhatJobs", "J-Vers", "Adzuna",
    "Galois", "Mindmatch.ai", "Myjobhelper", "TransForce", "CV Library",
    "CDLlife", "PlacedApp", "IrishJobs", "Praca.pl", "AppJobs",
    "OfferUp", "JobsInNetwork", "Jobsora", "StellenSMS", "Dice",
    "SonicJobs", "Botson.ai", "CMP Jobs", "Health Ecareers", "Hokify",
    "JobHubCentral", "BoostPoint", "Jobs In Japan", "Daijob.com",
    "GaijinPot", "GoWork.pl", "deBanenSite.nl", "Pracuj.pl", "Xing",
    "PostJobFree", "Jobsdb", "Stellenanzeigen.de", "Jobs.at", "Jobs.ch",
    "JobUp", "Jobwinner", "Topjobs.ch", "Vetted Health", "Arya by Leoforce",
    "Welcome to the Jungle", "JobMESH", "Bakeca.it", "Stack Overflow",
    "Diversity Jobs", "Laborum", "Curriculum", "American Nurses Association",
    "Profesia", "CareerCross", "Jobs.ie", "Nexxt", "Resume-Library.com",
    "Women for Hire", "Professional Diversity Network", "Rabota.bg",
    "Zaplata.bg", "Jobnet", "New Zealand Jobs", "Nationale Vacaturebank",
    "Intermediair", "eFinancialCareers", "Profession.hu", "Job Bank",
    "Personalwerk", "Yapo", "Karriere.at", "SAPO Emprego", "Catho",
    "Totaljobs", "Handshake", "Ladders.com", "Gumtree", "Instawork",
    "LinkedIn", "Facebook", "Instagram", "Google Ads", "Craigslist",
    "Reddit", "YouTube", "Spotify", "Jobbland", "Wonderkind",
    "adway.ai", "HeyTempo", "Otta", "Info Jobs", "Vagas",
    "Visage Jobs", "Hunar.ai", "CollabWORK", "Arbeitnow", "Doximity",
    "VietnamWorks", "JobKorea", "JobIndex", "HH.ru", "Consultants 500",
    "YM Careers", "Dental Post", "Foh and Boh", "Study Smarter",
    "Pnet", "Remote.co", "FATj", "Expresso Emprego", "Bravado",
]

_P1_P2_SORTED = sorted(P1_P2_PUBLISHERS)
_BATCH_SIZE = len(_P1_P2_SORTED) // 3
P1_P2_BATCHES: list[list[str]] = [
    _P1_P2_SORTED[:_BATCH_SIZE],
    _P1_P2_SORTED[_BATCH_SIZE: _BATCH_SIZE * 2],
    _P1_P2_SORTED[_BATCH_SIZE * 2:],
]
