from yt_dlp.extractor.common import InfoExtractor
import re
import json
import time
from bs4 import BeautifulSoup
from yt_dlp.utils import (
    OnDemandPagedList,
    parse_iso8601,
    traverse_obj,
    int_or_none,
    try_get,
    urlencode_postdata,
)
import urllib.parse

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
            'age_limit': 18,
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
        # Implement your method to extract categories here
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
        img = soup.find('img', alt=True, src=re.compile(r'/profiles/'))
        if img:
            return img['alt'].strip()

        for img in soup.find_all('img', alt=True):
            alt = img['alt'].strip()
            if not alt:
                continue
            if alt.lower() == 'logo':
                continue
            if alt.startswith('Thumbnail at '):
                continue
            return alt

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

        # collect .mp4 URLs (video.pmvhaven.com and storage.pmvhaven.com)
        # score candidates 1. video.pmvhaven.com, 2. if first path segment looks like this page's video id, 3. bonus if slug/title words appear in the URL, 4. penalize /videoPreview/ or /previews/
        # pick highest-scoring
        
        import urllib.parse

        webpage = str(soup)

        title = self._extract_title(soup) or ''
        title_norm = re.sub(r'\s+', ' ', title).strip().lower()

        page_vid = self._search_regex(
            r'_([0-9a-fA-F]{24})', url, 'video id', default=None)

        slug = None
        m_slug = re.search(r'/video/([^_?]+)_[0-9a-fA-F]{24}', url)
        if m_slug:
            slug = urllib.parse.unquote(m_slug.group(1))
        slug_words = [w.lower() for w in re.split(r'[-_\s]+', slug or '') if len(w) > 2]

        width = self._extract_width(soup)
        height = self._extract_height(soup)
        resolution = f'{width}x{height}' if width and height else None

        def is_preview(u: str) -> bool:
            u = u.lower()
            return '/videopreview/' in u or '/previews/' in u

        def normalize_url(vurl: str) -> str:
            if not vurl:
                return vurl
            vurl = vurl.strip()
            if not vurl.startswith('http'):
                vurl = 'https://' + vurl.lstrip('/')
            parsed = urllib.parse.urlsplit(vurl)
            path = urllib.parse.quote(parsed.path, safe='/%')
            return urllib.parse.urlunsplit(
                (parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment)
            )

        candidates = []

        def add_candidate(vurl: str, base_score: int = 0, source: str = ''):
            vurl = normalize_url(vurl)
            if not vurl:
                return

            parsed = urllib.parse.urlsplit(vurl)
            path_parts = parsed.path.strip('/').split('/')
            first_seg = path_parts[0] if path_parts else ''
            id_in_url = first_seg if re.match(r'^[0-9a-fA-F]{24}$', first_seg) else None

            url_l = vurl.lower()
            score = base_score

            if is_preview(url_l):
                score -= 20

            if parsed.netloc.startswith('video.pmvhaven.com'):
                score += 10
            elif parsed.netloc.startswith('storage.pmvhaven.com'):
                score += 0

            if page_vid and id_in_url and id_in_url.lower() == page_vid.lower():
                score += 10

            for w in slug_words:
                if w and w in url_l:
                    score += 2

            for w in re.split(r'\s+', title_norm):
                if len(w) > 3 and w in url_l:
                    score += 1

            candidates.append({
                'url': vurl,
                'score': score,
                'is_preview': is_preview(url_l),
                'source': source,
            })

        _SEP = r'(?:/|\\u002F)'
        mp4_patterns = [
            rf'https?:{_SEP}{_SEP}video\.pmvhaven\.com{_SEP}[^"\'<>\s]+?\.mp4',
            rf'https?:{_SEP}{_SEP}storage\.pmvhaven\.com{_SEP}[^"\'<>\s]+?\.mp4',
        ]
        for pattern in mp4_patterns:
            for u in re.findall(pattern, webpage):
                u = u.replace('\\u002F', '/')  # decode JSON unicode escapes
                add_candidate(u, base_score=0, source='scan')

        video_meta = soup.find('meta', attrs={'property': 'og:video:secure_url'})
        if not video_meta:
            video_meta = soup.find('meta', attrs={'name': 'twitter:player'})
        if video_meta and video_meta.get('content'):
            add_candidate(video_meta['content'], base_score=-5, source='meta')

        if not candidates:
            return []

        unique = {}
        for c in candidates:
            u = c['url']
            if u not in unique or c['score'] > unique[u]['score']:
                unique[u] = c

        all_cands = list(unique.values())

        non_preview = [c for c in all_cands if not c['is_preview']]
        chosen_pool = non_preview or all_cands

        best = max(chosen_pool, key=lambda c: (c['score'], len(c['url'])))

        fmt = {
            'url': best['url'],
            'ext': 'mp4',
            'http_headers': {'Referer': url},
        }
        if resolution:
            fmt['resolution'] = resolution

        m_h = re.search(r'(\d{3,4})p', best['url'])
        if m_h:
            h = int_or_none(m_h.group(1))
            if h:
                fmt['height'] = h

        return [fmt]

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

class PMVHavenUserIE(InfoExtractor):
    IE_NAME = 'pmvhaven:user'
    _VALID_URL = r'https?://(?:www\.)?pmvhaven\.com/profile/(?P<id>[\w.-]+)'

    _VIDEOS_API = 'https://pmvhaven.com/api/videos'
    _PAGE_SIZE = 100  

    _TESTS = [{
        'url': 'https://pmvhaven.com/profile/wezzam',

        'info_dict': {'id': 'wezzam', 'title': "wezzam"},
        'playlist_mincount': 1,
    }]

    def _extract_user_id_from_html(self, webpage, fallback_slug):

        m = re.search(r'/banners/([0-9a-fA-F]{24})-', webpage)
        if m:
            return m.group(1)
        return fallback_slug

    def _extract_profile_title(self, soup, fallback_slug):
        og = soup.find('meta', attrs={'property': 'og:title'})
        if og and og.get('content'):
            title = og['content']

            m = re.match(r"(.+?)'s Profile$", title)
            if m:
                return m.group(1)
            return title

        if soup.title and soup.title.string:
            return soup.title.string.strip()
        return fallback_slug

    def _fetch_videos_page(self, uploader_id, page):
        query = {
            'uploader': uploader_id,
            'limit': self._PAGE_SIZE,
            'page': page,
        }
        resp = self._download_json(
            self._VIDEOS_API,
            uploader_id,
            note=f'Downloading PMVHaven profile videos JSON page {page}',
            query=query)

        videos = traverse_obj(resp, ('videos', {list})) or []
        total_pages = int_or_none(traverse_obj(resp, ('pagination', 'totalPages')))
        return videos, (total_pages or page)

    def _build_video_result(self, video_obj, uploader_name):
        vid = traverse_obj(video_obj, ('_id', {str}))
        if not vid:
            return None

        title = traverse_obj(video_obj, ('title', {str})) or vid

        webpage_url = f'https://pmvhaven.com/video/video_{vid}'

        ie_result = self.url_result(
            webpage_url,
            ie=PMVHavenVideoIE.ie_key(),
            video_id=vid,
            video_title=title,
        )

        iso = traverse_obj(video_obj, ('isoDate', {str})) or traverse_obj(video_obj, ('createdAt', {str}))
        thumb_list = traverse_obj(video_obj, ('thumbnails', {list})) or []
        if not thumb_list:
            single_thumb = traverse_obj(video_obj, ('thumbnailUrl', {str}))
            if single_thumb:
                thumb_list = [single_thumb]
        thumbs = [{'url': t} for t in thumb_list if isinstance(t, str)]
        views = int_or_none(traverse_obj(video_obj, ('views', {int, str})))

        ie_result.update({
            'thumbnails': thumbs or None,
            'timestamp': parse_iso8601(iso),
            'uploader': uploader_name,
            'view_count': views,
        })
        return ie_result

    def _entries_from_api(self, uploader_id, uploader_name):
        page = 1
        total_pages = None
        while True:
            videos, reported_total = self._fetch_videos_page(uploader_id, page)
            if not videos:
                break

            if total_pages is None:
                total_pages = reported_total

            for v in videos:
                res = self._build_video_result(v, uploader_name)
                if res:
                    yield res

            page += 1
            if total_pages is not None and page > total_pages:
                break

    def _entries_from_html(self, webpage, user_slug, uploader_name):
        soup = BeautifulSoup(webpage, 'html.parser')
        seen = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/video/' not in href:
                continue
            if href.startswith('/'):
                href = 'https://pmvhaven.com' + href
            vid = self._search_regex(
                r'_([a-fA-F0-9]{24})',
                href,
                'video id',
                default=None)
            if not vid or vid in seen:
                continue
            seen.add(vid)
            title = (a.get('title')
                     or a.get('aria-label')
                     or a.get_text(strip=True)
                     or vid)
            yield self.url_result(
                href,
                ie=PMVHavenVideoIE.ie_key(),
                video_id=vid,
                video_title=title,
            )

    def _real_extract(self, url):
        user_slug = self._match_id(url)

        webpage = self._download_webpage(url, user_slug)
        soup = BeautifulSoup(webpage, 'html.parser')

        uploader_id = self._extract_user_id_from_html(webpage, user_slug)
        uploader_name = self._extract_profile_title(soup, user_slug)

        entries = list(self._entries_from_api(uploader_id, uploader_name))

        if not entries:
            entries = list(self._entries_from_html(webpage, user_slug, uploader_name))

        playlist_id = uploader_id
        playlist_title = uploader_name

        return self.playlist_result(entries, playlist_id=playlist_id, playlist_title=playlist_title)
