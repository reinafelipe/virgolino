import config

def check():
    placeholders = ["your_api_key_here", "your_secret_here", "your_passphrase_here", "your_private_key_here"]
    
    issues = []
    if config.API_KEY in placeholders: issues.append("API_KEY is default")
    if config.API_SECRET in placeholders: issues.append("API_SECRET is default")
    if config.API_PASSPHRASE in placeholders: issues.append("API_PASSPHRASE is default")
    if config.PRIVATE_KEY in placeholders: issues.append("PRIVATE_KEY is default")
    
    if issues:
        print("CREDENTIAL ISSUES FOUND:")
        for i in issues: print(i)
    else:
        print("Credentials look changed (not using defaults).")

if __name__ == "__main__":
    check()
