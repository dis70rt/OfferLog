# The base query:
# - label:JobHunt -> Only fetch emails with this exact label.
# The 'after:' time filter will be dynamically added in main.py (last 13 hours)
GMAIL_JOB_SEARCH_QUERY = "label:JobHunt"

# ---------------------------------------------------------
# (Archived) The old, complex keyword-based query 
# ---------------------------------------------------------
# GMAIL_JOB_SEARCH_QUERY = """(
#   subject:(
#     application OR applied OR interview OR interviewing OR
#     "phone screen" OR "technical screen" OR "technical interview" OR
#     assessment OR "coding challenge" OR "coding test" OR
#     "take-home" OR "take home" OR
#     "offer letter" OR
#     rejected OR rejection OR
#     "not moving forward" OR
#     "next steps" OR
#     "status update" OR
#     "hiring team" OR
#     onboarding OR
#     "background check" OR
#     shortlisted OR
#     "final round"
#   )
#   OR "please complete the assessment"
#   OR "coding assessment"
#   OR "complete your assessment"
#   OR "test link"
#   OR "assessment link"
#   OR "schedule your interview"
#   OR "we'd like to schedule"
#   OR "move forward with your application"
#   OR "thank you for applying"
#   OR from:(
#     greenhouse.io OR lever.co OR myworkday.com OR icims.com OR
#     smartrecruiters.com OR taleo.net OR bamboohr.com OR jobvite.com OR
#     ashbyhq.com OR hirevue.com OR hackerrank.com OR codility.com OR
#     karat.com OR metaview.ai OR codesignal.com OR breezy.hr OR workable.com
#   )
# )
# -category:promotions
# -category:social
# -category:forums
# -from:(
#   linkedin.com OR indeed.com OR glassdoor.com OR ziprecruiter.com OR
#   naukri.com OR monster.com OR simplyhired.com OR ycombinator.com OR
#   angel.co OR wellfound.com
# )
# -subject:(
#   "jobs for you" OR "new jobs" OR "job alert" OR "jobs matching" OR
#   "recommended jobs" OR digest OR newsletter OR unsubscribe
# )
# -(from:(
#   support@educative.io OR promotions@campaigns.magzter.com OR
#   noreply@medium.com OR hello@careercamp.codingninjas.com OR
#   information@hdfcbank.net OR noreply@github.com OR
#   notifications@github.com OR hello@roboflow.com OR
#   connect@paniitalumniindia.mails.org.in OR zach.m@educative.io OR
#   noreply@unstop.news OR bogdan@letsgetrusty.com OR
#   futrprf@substack.com OR karozieminski@substack.com OR
#   noreply@dare2compete.news OR info@interviewbit.com OR
#   student@mail.internshala.com OR no-reply@geeksforgeeks.org OR
#   Coursera@m.learn.coursera.org
# ))""".replace('\n', ' ')
