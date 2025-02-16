import urllib.parse
import requests
from datetime import datetime, timedelta

# OAuth Configuration
CLIENT_ID = '86qyzk1ldm4m0n'
CLIENT_SECRET = 'WPL_AP1.DCyCyz4ImWuLnokI.0SjFTA=='
REDIRECT_URI = 'https://67a76e73aa02f.site123.me'
SCOPES = 'openid profile w_member_social email rw_organization_admin r_compliance'

# API Endpoints
BASE_URL = 'https://api.linkedin.com/v2'

def authenticate():
    """Handle OAuth 2.0 authentication flow"""
    auth_url = (
        f'https://www.linkedin.com/oauth/v2/authorization?'
        f'response_type=code&'
        f'client_id={CLIENT_ID}&'
        f'redirect_uri={urllib.parse.quote(REDIRECT_URI)}&'
        f'scope={urllib.parse.quote(SCOPES)}&'
        f'state=linkedin_analytics'
    )
    print(f'Authorize here: {auth_url}')
    code = input('Enter authorization code: ').strip()
    
    token_url = 'https://www.linkedin.com/oauth/v2/accessToken'
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    return response.json()['access_token']

def get_organization_urn(access_token):
    """Retrieve first accessible organization URN"""
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(
        f'{BASE_URL}/organizationAcls?q=roleAssignee',
        headers=headers
    )
    response.raise_for_status()
    return response.json()['elements'][0]['organizationalTarget']

def get_analytics(access_token, org_urn):
    """Retrieve comprehensive organizational metrics"""
    headers = {'Authorization': f'Bearer {access_token}'}
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Format dates in milliseconds since epoch
    time_range = {
        'start': int(start_date.timestamp() * 1000),
        'end': int(end_date.timestamp() * 1000)
    }

    # Follower Statistics
    follower_stats = requests.get(
        f'{BASE_URL}/organizationalEntityFollowerStatistics',
        params={'q': 'organizationalEntity', 'organizationalEntity': org_urn},
        headers=headers
    ).json()

    # Page View Analytics
    page_views = requests.get(
        f'{BASE_URL}/organizationPageAnalytics',
        params={
            'q': 'organization',
            'organization': org_urn,
            'pivots': 'PAGE_SECTION',
            'timeIntervals.timeRange': f'(start:{time_range["start"]},end:{time_range["end"]})',
            'metrics': 'views'
        },
        headers=headers
    ).json()

    # Share Statistics
    shares = requests.get(
        f'{BASE_URL}/shares',
        params={
            'q': 'owners',
            'owners': org_urn,
            'count': 100,
            'timeIntervals.timeRange': f'(start:{time_range["start"]},end:{time_range["end"]})'
        },
        headers=headers
    ).json()

    return {
        'follower_stats': follower_stats,
        'page_views': page_views,
        'shares': shares
    }

def process_metrics(data):
    """Transform raw API data into structured metrics"""
    metrics = {
        'followers': data['follower_stats'].get('followerGains', 0),
        'reach': sum(s['totalShareStatistics']['viewCount'] for s in data['shares']['elements']),
        'impressions': sum(s['totalShareStatistics']['impressionCount'] for s in data['shares']['elements']),
        'interactions': {
            'comments': sum(s['totalShareStatistics']['commentCount'] for s in data['shares']['elements']),
            'likes': sum(s['totalShareStatistics']['likeCount'] for s in data['shares']['elements']),
            'clicks': sum(s['totalShareStatistics']['clickCount'] for s in data['shares']['elements']),
            'shares': sum(s['totalShareStatistics']['shareCount'] for s in data['shares']['elements'])
        },
        'profile_views': {
            'all_pages': sum(p['views'] for p in data['page_views']['elements']),
            'sections': {p['pageSection']: p['views'] 
                        for p in data['page_views']['elements']}
        },
        'top_shares': sorted(
            [(s['text']['text'], s['totalShareStatistics']['viewCount']) 
             for s in data['shares']['elements']],
            key=lambda x: x[1], 
            reverse=True
        )[:5]
    }
    return metrics

def main():
    access_token = authenticate()
    org_urn = get_organization_urn(access_token)
    raw_data = get_analytics(access_token, org_urn)
    metrics = process_metrics(raw_data)
    
    print(f"\nNew Followers: {metrics['followers']}")
    print(f"Reach: {metrics['reach']}")
    print(f"Impressions: {metrics['impressions']}")
    print("\nEngagement Metrics:")
    for k, v in metrics['interactions'].items():
        print(f"- {k.title()}: {v}")
    
    print("\nProfile Views:")
    print(f"- Total: {metrics['profile_views']['all_pages']}")
    for section, views in metrics['profile_views']['sections'].items():
        print(f"- {section}: {views}")
    
    print("\nTop Shared Content:")
    for idx, (content, views) in enumerate(metrics['top_shares'], 1):
        print(f"{idx}. {content[:50]}... ({views} views)")

if __name__ == "__main__":
    main()