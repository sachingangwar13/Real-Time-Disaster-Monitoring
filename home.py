import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import plotly.express as px
from wordcloud import WordCloud
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()


def main():
    # MongoDB Atlas connection URI
    uri = os.getenv('MONGODB_URI')
    client = MongoClient(uri)

    # Access the GeoNews database and collection
    db = client["GeoNews"]
    collection = db["disaster_info"]

    exclude_locations = ['pakistan']
    
    # Load data from MongoDB
    df = pd.DataFrame(list(collection.find()))

    if 'timestamp' in df.columns:
        # Ensure timestamps are in datetime format
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    else:
        df['timestamp'] = pd.NaT

    df.drop_duplicates(subset='title', inplace=True)

    if 'Latitude' in df.columns and 'Longitude' in df.columns:
        df = df.dropna(subset=['Latitude', 'Longitude'])
    else:
        st.error("Latitude and/or Longitude columns are missing in the dataset.")
        return

    df = df[~df['Location'].str.lower().isin(exclude_locations)]
    df = df[~df['url'].str.lower().str.contains('politics|yahoo|sports')]
    df = df[~df['title'].str.lower().str.contains('tool|angry')]

    # Drop duplicates based on specific criteria
    df['date_only'] = df['timestamp'].dt.strftime('%Y-%m-%d')
    df.drop_duplicates(subset=['date_only', 'disaster_event', 'Location'], inplace=True)
    df.drop(columns=['date_only'], inplace=True)

    # Sidebar filters
    st.title("Real-Time Disaster Information Aggregation Software")
    selected_events = st.multiselect(
        "Select Disaster Events",
        ["All"] + list(df["disaster_event"].unique()),
        default=["All"],
    )

    start_date = st.sidebar.date_input(
        "Start date", 
        datetime.utcnow().date() - timedelta(days=7), 
        min_value=datetime(2023, 1, 1).date(), 
        max_value=datetime.utcnow().date()
    )
    end_date = st.sidebar.date_input(
        "End date",
        datetime.utcnow().date(),
        min_value=start_date,
        max_value=datetime.utcnow().date()
    )

    start_date_utc = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_date_utc = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)

    if "All" in selected_events:
        filtered_df = df[(df['timestamp'] >= start_date_utc) & (df['timestamp'] <= end_date_utc)]
    else:
        filtered_df = df[
            (df['timestamp'] >= start_date_utc) &
            (df['timestamp'] <= end_date_utc) &
            (df['disaster_event'].isin(selected_events))
        ]

    if filtered_df.empty:
        st.subheader(":green[No Disaster data available after filtering based on the condition]")
    else:
        # Map visualization
        map_center = (filtered_df['Latitude'].mean(), filtered_df['Longitude'].mean())
        mymap = folium.Map(location=map_center, zoom_start=4, fullscreen_control=True)
        folium.TileLayer(
            'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            attr='&copy; OpenStreetMap contributors',
            name='OpenStreetMap (English)'
        ).add_to(mymap)
        marker_cluster = MarkerCluster().add_to(mymap)

        def get_custom_icon_path(disaster_event):
            
            icon_paths = {
                "avalanche": 'https://cdn-icons-png.flaticon.com/128/67/67855.png',
                "blizzard": 'https://cdn-icons-png.flaticon.com/128/5213/5213532.png',
                "cyclone": 'https://cdn-icons-png.flaticon.com/128/3682/3682921.png',
                "drought": 'https://cdn-icons-png.flaticon.com/128/1098/1098132.png',
                "earthquake": 'https://cdn-icons-png.flaticon.com/128/8545/8545362.png',
                'flood': 'https://cdn-icons-png.flaticon.com/128/2347/2347728.png',
                "heatwave": 'https://cdn-icons-png.flaticon.com/128/7110/7110118.png',
                "hurricane": 'https://cdn-icons-png.flaticon.com/128/6631/6631998.png',
                "landslide": 'https://cdn-icons-png.flaticon.com/128/3920/3920979.png',
                "storm": 'https://cdn-icons-png.flaticon.com/128/3236/3236885.png',
                "tornado": 'https://cdn-icons-png.flaticon.com/128/803/803497.png',
                "tsunami": 'https://cdn-icons-png.flaticon.com/128/533/533077.png',
                "volcano": 'https://cdn-icons-png.flaticon.com/128/2206/2206570.png',
                "wildfire": 'https://cdn-icons-png.flaticon.com/128/2904/2904019.png',
            }
            return icon_paths.get(disaster_event, 'https://cdn-icons-png.flaticon.com/128/4357/4357606.png')

        for _, row in filtered_df.iterrows():
            custom_icon_path = get_custom_icon_path(row['disaster_event'])
            custom_icon = folium.CustomIcon(
                icon_image=custom_icon_path,
                icon_size=(35, 35),
                icon_anchor=(15, 30),
                popup_anchor=(0, -25)
            )            
            popup_content = f"<a href='{row['url']}' target='_blank'>{row['title']}</a>"
            tooltip_content = f"{row['disaster_event']}, {row['Location']}"
            folium.Marker(
                location=[row['Latitude'], row['Longitude']],
                tiles='Stamen Toner',
                popup=folium.Popup(popup_content, max_width=300),
                icon=custom_icon,
                tooltip=tooltip_content
            ).add_to(marker_cluster)
            
            base_map_styles = {
            'Terrain': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Physical_Map/MapServer/tile/{z}/{y}/{x}',
            'Satellite': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            'Ocean': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}',
            'Detail': 'https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}'
            }

        # Add base map styles as layers
        for name, url in base_map_styles.items():
            folium.TileLayer(url, attr="Dummy Attribution", name=name).add_to(mymap)

        # Add layer control to the map with collapsed=True to hide the additional layers
        folium.LayerControl(collapsed=True).add_to(mymap)

        st_folium(mymap, width='100%', height=620)

        # Display filtered data
        with st.expander(f"Disaster Data Overview"):
            st.markdown(f"### Disaster Data for {'All Events' if 'All' in selected_events else ', '.join(selected_events)}")
            st.write(filtered_df[['title', 'disaster_event', 'timestamp', 'source', 'url', 'Location']])

    # Marquee section
    marquee_df = df[df['disaster_event'].isin(["Earthquake", "Flood", "Cyclone", "Volcano"])]
    seven_days_ago = pd.Timestamp(datetime.utcnow() - timedelta(days=7), tz="UTC")
    marquee_df = marquee_df[marquee_df['timestamp'] >= seven_days_ago].sort_values(by='timestamp', ascending=False)

    marquee_content = "".join(
        f"<a href='{row['url']}' target='_blank' style='color:white;'>{row['title']}</a> <br>" for _, row in marquee_df.iterrows()
    )
    print(marquee_content)
    marquee_html = f"""
        <h1>Key Events</h1>
        <div class="marquee-container" onmouseover="stopMarquee()" onmouseout="startMarquee()">
            <div class="marquee-content">{marquee_content}</div>
        </div>
        <style>
            .marquee-container {{
                height: 100%;
                overflow: hidden;
            }}
            .marquee-content {{
                animation: marquee 40s linear infinite;
            }}
            @keyframes marquee {{
                0%   {{ transform: translateY(100%); }}
                100% {{ transform: translateY(-100%); }}
            }}
        </style>
        <script>
            function stopMarquee() {{
                document.querySelector('.marquee-content').style.animationPlayState = 'paused';
            }}
            function startMarquee() {{
                document.querySelector('.marquee-content').style.animationPlayState = 'running';
            }}
        </script>
    """
    st.sidebar.markdown(marquee_html, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
