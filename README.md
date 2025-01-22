# Sub-Domain Enumeration

## Notes
 Here we perform subdomain enumeration using 2 popular techniques:
 1. Google Search Engine
 2. Crt.sh certificate domain

## Steps to run the Program
1. Git clone the repo: `` git clone ``
2. Create a Virtual Env `` python3 -m venv .venv ``
3. Activate the Virtual Environment `` source .venv/bin/activate ``
4. Install the necessary packages `` pip install -r requirments.txt``
5. Populate the .env file with the following details:
    ```  
        cx = "Your_Google_CX_Key"
        api_key = "Your_API_Key"
        user_agent = "Custom_User_Agent"
    ```
6. Run the Program with the command `` python3 subDomainEnum.py ``
7. Enter the domain name eg: ``example.com``

The subdomains will be given