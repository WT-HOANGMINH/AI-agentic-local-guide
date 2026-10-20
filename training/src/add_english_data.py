
from pathlib import Path
import shutil
import pandas as pd

# Thu muc goc cua du an
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "training" / "data" / "intents.csv"

# 30 cau tieng Anh cho moi nhan
ENGLISH_DATA = {
    "food": [
        "Where can I eat good local food in Da Nang?",
        "Recommend a restaurant serving authentic Vietnamese food.",
        "Where can I try Mi Quang in Da Nang?",
        "What local specialties should I try in Da Nang?",
        "Find a good restaurant near Dragon Bridge.",
        "Where can I eat affordable seafood in Da Nang?",
        "Suggest a place for traditional Vietnamese breakfast.",
        "What is a good place to eat Banh Mi in Da Nang?",
        "Recommend a restaurant for a family dinner.",
        "Where can I find delicious Bun Cha Ca?",
        "Find a restaurant with vegetarian food.",
        "Where can I eat local food on a small budget?",
        "Suggest a restaurant popular with local people.",
        "What seafood restaurants are worth visiting?",
        "Where can I get a late dinner in Da Nang?",
        "Recommend a place to eat Vietnamese noodles.",
        "Find a restaurant near My Khe Beach.",
        "Where should I eat lunch in the city center?",
        "What are the best local dishes in Da Nang?",
        "Suggest an affordable place for dinner.",
        "Where can I try authentic Vietnamese cuisine?",
        "Find a restaurant suitable for a group of friends.",
        "Recommend a place for fresh seafood.",
        "Where can I get a quick meal near the airport?",
        "What restaurant serves good local specialties?",
        "Suggest a place to eat traditional Vietnamese food.",
        "Where can I find good street food in Da Nang?",
        "Recommend a restaurant with a quiet atmosphere.",
        "Find a local food place open for breakfast.",
        "Where can I eat delicious food near the Han River?",
    ],
    "cafe": [
        "Recommend a quiet cafe where I can study.",
        "Where can I find a beautiful cafe in Da Nang?",
        "Find a coffee shop near Dragon Bridge.",
        "Suggest a cafe with reliable Wi-Fi.",
        "Where can I work remotely with my laptop?",
        "Recommend a cafe with a sea view.",
        "Find a quiet coffee shop for reading.",
        "Where can I drink coffee near My Khe Beach?",
        "Suggest an affordable cafe for students.",
        "Which cafes have comfortable seats for studying?",
        "Find a cafe with a nice interior for photos.",
        "Recommend a coffee shop open early in the morning.",
        "Where can I enjoy Vietnamese coffee?",
        "Suggest a cafe suitable for working all afternoon.",
        "Find a coffee shop near the city center.",
        "Where can I get good iced milk coffee?",
        "Recommend a cafe with a peaceful atmosphere.",
        "Which cafes are good for meeting friends?",
        "Find a cafe with power outlets for my laptop.",
        "Where can I enjoy coffee with a river view?",
        "Suggest a cafe that is not too crowded.",
        "Recommend a place for coffee and dessert.",
        "Where can I find a modern cafe in Da Nang?",
        "Find a coffee shop suitable for remote work.",
        "Which cafe has a good view of the city?",
        "Recommend a small and cozy coffee shop.",
        "Where can I study with friends over coffee?",
        "Find a cafe near the airport.",
        "Suggest a cafe with outdoor seating.",
        "Where can I relax and drink coffee in Da Nang?",
    ],
    "attraction": [
        "What are the best places to visit in Da Nang?",
        "Recommend popular tourist attractions in the city.",
        "Where should I go sightseeing in Da Nang?",
        "Find interesting places near Dragon Bridge.",
        "What can I visit near My Khe Beach?",
        "Suggest cultural attractions in Da Nang.",
        "Where can I enjoy beautiful mountain scenery?",
        "Recommend a place to watch the sunset.",
        "What are some famous landmarks in Da Nang?",
        "Find a good place for landscape photography.",
        "Where can I explore local history and culture?",
        "Suggest attractions suitable for families.",
        "What should I see during my first visit?",
        "Recommend a scenic place near the city center.",
        "Where can I visit temples or pagodas?",
        "Find tourist attractions suitable for children.",
        "What are the must-see places in Da Nang?",
        "Where can I enjoy views of the ocean?",
        "Recommend a nature destination near Da Nang.",
        "What places are good for taking photos?",
        "Find a famous bridge worth visiting.",
        "Where can I explore the local culture?",
        "Suggest an attraction for a rainy day.",
        "What are some hidden gems in Da Nang?",
        "Recommend a place to walk and enjoy the scenery.",
        "Where can I see the city from above?",
        "Find interesting places for a solo traveler.",
        "What attractions are close to the Han River?",
        "Recommend a peaceful place away from crowds.",
        "Where should tourists go in Da Nang?",
    ],
    "itinerary": [
        "Plan a one-day trip to Da Nang.",
        "Create a two-day itinerary for Da Nang.",
        "I have three days in Da Nang. Where should I go?",
        "Plan a trip within a budget of 500,000 VND.",
        "Create a travel itinerary for a family.",
        "Help me plan a weekend in Da Nang.",
        "Make a schedule for sightseeing and local food.",
        "Plan a trip focused on beaches and nature.",
        "Create a food tour itinerary for one day.",
        "Plan a half-day sightseeing trip.",
        "Suggest a travel plan for first-time visitors.",
        "Build an itinerary with cafes and attractions.",
        "Plan a budget-friendly day in Da Nang.",
        "Create a two-day trip with cultural attractions.",
        "Help me organize my sightseeing schedule.",
        "Plan a relaxing trip without too many activities.",
        "Make an itinerary for a solo traveler.",
        "Plan a day trip with my family and children.",
        "Create a route to visit the main attractions.",
        "Suggest a three-day travel plan for Da Nang.",
        "Plan a trip that includes beaches and seafood.",
        "Make a travel schedule for a rainy day.",
        "Create an itinerary based on a limited budget.",
        "Plan a morning and afternoon sightseeing route.",
        "Help me decide what to do during my stay.",
        "Create a travel plan for two people.",
        "Plan a trip with photography spots and cafes.",
        "Make an itinerary with minimal travel time.",
        "Suggest activities for a free afternoon in Da Nang.",
        "Organize a full day of sightseeing in Da Nang.",
    ],
    "transport": [
        "How do I get from the airport to Dragon Bridge?",
        "Should I take a bus or a taxi in Da Nang?",
        "Give me directions to My Khe Beach.",
        "What is the easiest way to get around Da Nang?",
        "How can I travel from the city center to the airport?",
        "Find a bus route to the city center.",
        "How long does it take to reach My Khe Beach?",
        "Should I rent a motorbike or use a taxi?",
        "How can I get to Marble Mountains?",
        "Suggest an affordable way to travel around the city.",
        "How do I get from Dragon Bridge to the beach?",
        "What transport options are available from the airport?",
        "Give me directions to the Han Market.",
        "How can I travel to Ba Na Hills?",
        "Is it easy to use public buses in Da Nang?",
        "Find the best way to reach the city center.",
        "How much does a taxi to My Khe Beach cost?",
        "Which transport option is best for a short trip?",
        "How do I get to the train station?",
        "Can I walk from Dragon Bridge to the city center?",
        "Suggest transport for a family with luggage.",
        "How can I get around without renting a motorbike?",
        "Give me directions to the nearest bus stop.",
        "What is the fastest way to reach the airport?",
        "How do I travel between tourist attractions?",
        "Should I use a ride-hailing app or a taxi?",
        "Find a convenient route to the beach.",
        "How can I get to the night market?",
        "What is the cheapest way to travel in Da Nang?",
        "Help me choose transport for sightseeing.",
    ],
}


def normalize_text(text):
    """Chuan hoa cau de phat hien trung lap."""
    return " ".join(str(text).strip().casefold().split()).rstrip(".,!?;:")


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Khong tim thay dataset: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)

    if not {"text", "label"}.issubset(df.columns):
        raise ValueError("Dataset phai co hai cot text va label.")

    df = df.dropna(subset=["text", "label"]).copy()
    df["text"] = df["text"].astype(str).str.strip()
    df["label"] = df["label"].astype(str).str.strip()

    expected_labels = set(ENGLISH_DATA)
    existing_labels = set(df["label"].unique())

    if not expected_labels.issubset(existing_labels):
        missing = expected_labels - existing_labels
        raise ValueError(f"Dataset thieu cac nhan: {sorted(missing)}")

    # Tao danh sach cau tieng Anh
    new_rows = []
    for label, sentences in ENGLISH_DATA.items():
        for sentence in sentences:
            new_rows.append({"text": sentence, "label": label})

    new_df = pd.DataFrame(new_rows)

    # Loai cau trung lap voi dataset cu va trong bo moi
    existing_keys = set(df["text"].map(normalize_text))
    new_df["_key"] = new_df["text"].map(normalize_text)
    before = len(new_df)

    new_df = new_df[~new_df["_key"].isin(existing_keys)]
    new_df = new_df.drop_duplicates(subset="_key", keep="first")
    new_df = new_df.drop(columns="_key")

    added_count = len(new_df)

    if added_count == 0:
        print("Khong co cau moi de them. Dataset duoc giu nguyen.")
        return

    # Sao luu truoc khi cap nhat
    backup_path = DATA_PATH.with_name("intents.backup.csv")
    if not backup_path.exists():
        shutil.copy2(DATA_PATH, backup_path)

    # Ghep du lieu va luu lai
    updated_df = pd.concat([df, new_df], ignore_index=True)
    updated_df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")

    print("HOAN TAT BO SUNG DU LIEU TIENG ANH")
    print(f"So cau tieng Anh du kien: {before}")
    print(f"So cau tieng Anh duoc them: {added_count}")
    print(f"So cau bi bo do trung lap: {before - added_count}")
    print(f"So mau truoc khi them: {len(df)}")
    print(f"So mau sau khi them: {len(updated_df)}")
    print(f"\nThong ke theo nhan:\n{updated_df['label'].value_counts().sort_index()}")
    print(f"\nFile dataset: {DATA_PATH}")
    print(f"File sao luu: {backup_path}")


if __name__ == "__main__":
    main()
