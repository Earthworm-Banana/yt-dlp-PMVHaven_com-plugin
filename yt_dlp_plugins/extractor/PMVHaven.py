from yt_dlp.extractor.common import InfoExtractor
from bs4 import BeautifulSoup
import re

class PMVHavenVideoIE(InfoExtractor):
    IE_NAME = 'pmvhaven:video'
    _VALID_URL = r'https?://(?:www\.)?pmvhaven\.com/video/[^_]+_(?P<id>[a-zA-Z0-9]+)'
    
    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        soup = BeautifulSoup(webpage, 'html.parser')

        title = self._extract_title(soup)
        uploader = self._extract_uploader(soup)
        categories = self._extract_categories(soup)
        tags = self._extract_tags(soup)
        music = self._extract_music(soup)
        creator = self._extract_creator(soup)
        stars = self._extract_stars(soup)
        description = self._extract_description(soup)
        duration = self._extract_duration(soup)
        view_count = self._extract_view_count(soup)
        upload_date = self._extract_upload_date(soup)
        thumbnail = self._extract_thumbnail(soup)
        formats = self._extract_formats(soup, url)
        video_meta = self._extract_video_meta(soup)

        return {
            'id': video_id,
            'title': title,
            'uploader': uploader,
            'categories': categories,
            'tags': tags,
            'music': music,
            'creator': creator,
            'stars': stars,
            'description': description,
            'duration': duration,
            'view_count': view_count,
            'upload_date': upload_date,
            'thumbnail': thumbnail,
            'formats': formats,
            **video_meta
        }

    def _extract_title(self, soup):
        title_meta = soup.find('meta', attrs={'property': 'og:title'})
        if title_meta:
            return title_meta['content']
        title_meta = soup.find('meta', attrs={'name': 'twitter:title'})
        if title_meta:
            return title_meta['content']
        return None

    def _extract_uploader(self, soup):
        uploader_meta = soup.find('meta', attrs={'name': 'author'})
        if uploader_meta:
            return uploader_meta['content']
        return None

    def _extract_categories(self, soup):
        # Implement your method to extract categories here
        return []

    def _extract_tags(self, soup):
        tags_meta = soup.find('meta', attrs={'property': 'og:video:tag'})
        if tags_meta:
            return tags_meta['content'].split(', ')
        keywords_meta = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_meta:
            return keywords_meta['content'].split(', ')
        return []

    def _extract_music(self, soup):
        # Implement your method to extract music here
        return []

    def _extract_creator(self, soup):
        # Implement your method to extract creator here
        return None

    def _extract_stars(self, soup):
        # Implement your method to extract stars here
        return []

    def _extract_description(self, soup):
        desc_meta = soup.find('meta', attrs={'name': 'description'})
        if desc_meta:
            return desc_meta['content']
        desc_meta = soup.find('meta', attrs={'property': 'og:description'})
        if desc_meta:
            return desc_meta['content']
        return None

    def _extract_duration(self, soup):
        duration_meta = soup.find('meta', attrs={'property': 'og:video:duration'})
        if duration_meta:
            return int(duration_meta['content'])
        return None

    def _extract_view_count(self, soup):
        # Implement your method to extract view count here
        return None

    def _extract_upload_date(self, soup):
        # Implement your method to extract upload date here
        return None

    def _extract_thumbnail(self, soup):
        thumbnail_meta = soup.find('meta', attrs={'property': 'og:image'})
        if thumbnail_meta:
            return thumbnail_meta['content']
        thumbnail_meta = soup.find('meta', attrs={'name': 'twitter:image'})
        if thumbnail_meta:
            return thumbnail_meta['content']
        return None

    def _extract_formats(self, soup, url):
        video_meta = soup.find('meta', attrs={'property': 'og:video:secure_url'})
        if not video_meta:
            video_meta = soup.find('meta', attrs={'name': 'twitter:player'})
        video_url = video_meta['content'] if video_meta else None
        width = self._extract_width(soup)
        height = self._extract_height(soup)
        resolution = f'{width}x{height}' if width and height else 'unknown'
        if video_url:
            return [{
                'url': video_url, 
                'format_id': 'mp4', 
                'ext': 'mp4', 
                'http_headers': {'Referer': f'{url}'},
                'vcodec': 'unknown',
                'acodec': 'unknown',
                'resolution': resolution
            }]
        return []

    def _extract_video_meta(self, soup):
        meta = {}
        width_meta = soup.find('meta', attrs={'property': 'og:video:width'})
        height_meta = soup.find('meta', attrs={'property': 'og:video:height'})
        if not width_meta:
            width_meta = soup.find('meta', attrs={'name': 'twitter:player:width'})
        if not height_meta:
            height_meta = soup.find('meta', attrs={'name': 'twitter:player:height'})

        if width_meta and height_meta:
            meta['width'] = int(width_meta['content'])
            meta['height'] = int(height_meta['content'])
        
        if 'width' in meta and 'height' in meta:
            meta['resolution'] = f"{meta['width']}x{meta['height']}"
        
        return meta

    def _extract_width(self, soup):
        width_meta = soup.find('meta', attrs={'property': 'og:video:width'})
        if not width_meta:
            width_meta = soup.find('meta', attrs={'name': 'twitter:player:width'})
        if width_meta:
            return int(width_meta['content'])
        return None

    def _extract_height(self, soup):
        height_meta = soup.find('meta', attrs={'property': 'og:video:height'})
        if not height_meta:
            height_meta = soup.find('meta', attrs={'name': 'twitter:player:height'})
        if height_meta:
            return int(height_meta['content'])
        return None
