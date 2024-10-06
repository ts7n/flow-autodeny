from dotenv import load_dotenv
from openai import OpenAI
import requests
import os

load_dotenv()
openai = OpenAI()

# Get story assignments submitted to the group

groups = requests.get("https://flow.snosites.com/api/v1/dashboard/groups", headers={
    "Cookie": os.environ.get("FLOW_COOKIE"),
    "x-xsrf-token": os.environ.get("FLOW_XSRF")
})
groups.raise_for_status()
groups = groups.json()

assignments = groups["assignments"][os.environ.get("GROUP_NAME")]

# Check for validity of assignments

for assignment in assignments:
    assignment = requests.get(f"https://flow.snosites.com/api/v1/assignment/{assignment['assignment_id']}", headers={
        "Cookie": os.environ.get("FLOW_COOKIE"),
        "x-xsrf-token": os.environ.get("FLOW_XSRF")
    })
    assignment.raise_for_status()
    assignment = assignment.json()

    print("Checking assignment:", assignment["title"])
    has_issues = False

    # Red flag #1: No images at all

    if len(assignment["images"]) == 0:
        print("  X) Images found = 0")
        has_issues = True
    else:
        print("  ✓) Images found ≥ 1")

        # Red flag #2: Images are not captioned and credited

        for image in assignment["images"]:
            if image["caption"] == "" or image["photographer"] == "":
                print("  X) Image not captioned/credited")
                has_issues = True
                break
        else:
            print("  ✓) Images all captioned/credited")
    
    # Red flag #3: Headline suspectedly not complete (w/ AI)

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "The user is going to provide either a finished article headline, or one that was used internally to describe the article. Your job is to respond with only \"yes\" or \"no\" to the following question: Is the headline a finalized one, or an internal one? The main way you should determine this is by considering if the headline is capitalized with title case, is mostly grammatically correct, and is not just a super super simple description. If you are less than ~75% confident, respond \"yes\". Examples of a finalized headline are \"Latin Students Dress to Impress for Spirit Week,\" or \"New Surveillance System Launched to Improve Campus Safety.\" Examples of internal ones are \"advanced math cancelled,\" \"new/returning teachers,\" or \"Science Grading System Opinion.\" One exception: any article containing \"Student of the Week\" or its acronym \"SoTW\", or \"Athlete of the Week\" or its acronym \"AotW\" should be considered finalized no matter what."
            },
            {
                "role": "user",
                "content": assignment["title"]
            }
        ]
    )

    if response.choices[0].message.content == "no":
        print("  X) Headline not finalized")
        has_issues = True
    else:
        print("  ✓) Headline finalized")
    
    # Return for revisions & notify editors if necessary

    if has_issues:
        print("  !) This assignment has issues; returning for revisions.")

        user = requests.get(f"https://flow.snosites.com/api/v1/user/{assignment['user_id']}", headers={
            "Cookie": os.environ.get("FLOW_COOKIE"),
            "x-xsrf-token": os.environ.get("FLOW_XSRF")
        })
        user.raise_for_status()
        user = user.json()

        requests.post("https://flow.snosites.com/api/v1/assignment/rejectGroup", headers={
            "Cookie": os.environ.get("FLOW_COOKIE"),
            "x-xsrf-token": os.environ.get("FLOW_XSRF")
        }, json={
            "assignment_id": assignment["assignments"][0]["id"],
            "group_id": int(os.environ.get("GROUP_ID"))
        })

print("Validation completed successfully.")