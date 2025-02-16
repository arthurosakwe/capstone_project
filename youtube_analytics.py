import os
import datetime
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = [
    'https://www.googleapis.com/auth/yt-analytics.readonly',
    'https://www.googleapis.com/auth/youtube.readonly'
]

def authenticate():
    """Handles OAuth2 authentication."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('youtubeAnalytics', 'v2', credentials=creds), build('youtube', 'v3', credentials=creds)

def get_analytics(youtube_analytics, youtube):
    """Retrieve and process analytics data."""
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    start_date = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")

    # Main metrics report (removed unsupported "impressions")
    main_metrics = youtube_analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date,
        endDate=end_date,
        metrics="views,estimatedMinutesWatched,subscribersGained,averageViewDuration",
        dimensions="day"
    ).execute()

    # Traffic sources report
    traffic_sources = youtube_analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date,
        endDate=end_date,
        metrics="views",
        dimensions="insightTrafficSourceType",
        sort="-views"
    ).execute()

    # Top videos report
    top_videos = youtube_analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date,
        endDate=end_date,
        metrics="views",
        dimensions="video",
        sort="-views",
        maxResults=5
    ).execute()

    return {
        'main_metrics': process_main_metrics(main_metrics),
        'traffic_sources': process_traffic_sources(traffic_sources),
        'top_videos': process_top_videos(top_videos, youtube)
    }

def process_main_metrics(data):
    """Process core metrics data."""
    headers = [h["name"] for h in data["columnHeaders"]]
    rows = data.get("rows", [])
    total_views = sum(row[headers.index("views")] for row in rows)
    total_watch_time = sum(row[headers.index("estimatedMinutesWatched")] for row in rows)
    new_subscribers = sum(row[headers.index("subscribersGained")] for row in rows)
    avg_view_duration = (
        sum(row[headers.index("averageViewDuration")] for row in rows) / len(rows)
        if rows else 0
    )
    return {
        "total_views": total_views,
        "total_watch_time": total_watch_time,
        "new_subscribers": new_subscribers,
        "avg_view_duration": format_duration(avg_view_duration)
    }

def process_traffic_sources(data):
    """Process traffic sources data."""
    return {row[0]: row[1] for row in data.get("rows", [])}

def process_top_videos(data, youtube):
    """Process and enrich top videos data."""
    video_ids = [row[0] for row in data.get("rows", [])]
    video_titles = get_video_titles(youtube, video_ids)
    # Create a dict mapping video title to views
    return {video_titles.get(row[0], row[0]): row[1] for row in data.get("rows", [])}

def get_video_titles(youtube, video_ids):
    """Get video titles from YouTube Data API."""
    response = youtube.videos().list(
        part="snippet",
        id=",".join(video_ids)
    ).execute()
    return {item["id"]: item["snippet"]["title"] for item in response.get("items", [])}

def format_duration(seconds):
    """Convert seconds to human-readable format."""
    minutes, seconds = divmod(seconds, 60)
    return f"{int(minutes)}m {int(seconds)}s"

def print_report(report):
    """Display formatted analytics report."""
    print("\n=== Channel Analytics Report (Last 30 Days) ===")
    
    # Main Metrics
    print("\nCore Metrics:")
    print(f"Total Views: {report['main_metrics']['total_views']:,}")
    print(f"Total Watch Time: {report['main_metrics']['total_watch_time']:,} minutes")
    print(f"New Subscribers: {report['main_metrics']['new_subscribers']:,}")
    print(f"Average View Duration: {report['main_metrics']['avg_view_duration']}")

    # Traffic Sources
    print("\nTraffic Sources:")
    for source, views in report['traffic_sources'].items():
        print(f"{source.replace('_', ' ').title()}: {views:,} views")

    # Top Videos
    print("\nTop Performing Videos:")
    for title, views in report['top_videos'].items():
        print(f"{title}: {views:,} views")

if __name__ == "__main__":
    youtube_analytics, youtube = authenticate()
    report = get_analytics(youtube_analytics, youtube)
    print_report(report)
