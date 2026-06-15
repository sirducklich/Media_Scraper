import pandas as pd
import difflib

# 1. Load the datasets
yippy_df = pd.read_csv("yippy.csv")
tier_df = pd.read_excel("16032026_ttb PR_Publisher Tier (Lasted update).xlsx")

# 2. Map platform names to ensure they align
platform_map = {
    'x': 'x/twitter',
    'twitter': 'x/twitter',
    'ig': 'instagram'
}

yippy_df['merge_platform'] = yippy_df['Platform'].astype(str).str.lower().str.strip().replace(platform_map)
tier_df['merge_platform'] = tier_df['Platform'].astype(str).str.lower().str.strip().replace(platform_map)

# Clean names by lowercasing and removing spaces for better baseline matching
tier_df['clean_publisher'] = tier_df['publusher_name'].astype(str).str.lower().str.replace(' ', '', regex=False)

# 3. Define the fuzzy matching function
def get_fuzzy_tier(row):
    outlet = str(row['Media_Outlet']).lower().strip()
    clean_outlet = outlet.replace(' ', '')
    platform = row['merge_platform']
    
    # Filter the reference file to only look at the same platform
    platform_tiers = tier_df[tier_df['merge_platform'] == platform]
    
    if platform_tiers.empty:
        return "Platform Not Found", "No Match"
        
    # Dictionary of cleaned publisher names to their Tiers and original names
    # Using dictionary comprehension to handle potential duplicates safely
    tier_dict = dict(zip(platform_tiers['clean_publisher'], platform_tiers['Tier']))
    name_dict = dict(zip(platform_tiers['clean_publisher'], platform_tiers['publusher_name']))
    
    # Check 1: Exact match after spaces are removed
    if clean_outlet in tier_dict:
        return tier_dict[clean_outlet], name_dict[clean_outlet]
        
    # Check 2: Substring match (e.g., 'forbesthailand' in 'forbesthailandmagazine')
    for pub_clean, tier in tier_dict.items():
        if clean_outlet in pub_clean or pub_clean in clean_outlet:
            return tier, name_dict[pub_clean]
            
    # Check 3: Fuzzy matching for typos using Python's built-in difflib
    # cutoff=0.6 means it requires at least a 60% similarity score
    possible_matches = difflib.get_close_matches(clean_outlet, tier_dict.keys(), n=1, cutoff=0.6)
    
    if possible_matches:
        best_match = possible_matches[0]
        return tier_dict[best_match], name_dict[best_match]
        
    return "Not Found", "No Match"

# 4. Apply the matching function
# This returns two columns: The Tier, and the name of the publisher it matched with (for your validation)
yippy_df[['Tier', 'Matched_With']] = yippy_df.apply(
    lambda row: pd.Series(get_fuzzy_tier(row)), axis=1
)

# 5. Clean up the helper column and export
yippy_df.drop(columns=['merge_platform'], inplace=True)

output_file = "yippy_fuzzy_tiered.csv"
yippy_df.to_csv(output_file, index=False)

print(f"Fuzzy mapping complete! File saved as {output_file}.")