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

        # Fetch the API endpoint
        api_res = self._download_json(
            f'https://pmvhaven.com/api/videos/{video_id}',
            video_id,
            fatal=False
        ) or {}
        api_data = api_res.get('data') or {}

        # Fetch the JSON-LD
        json_ld = self._extract_json_ld_video_object(soup)

        title = self._extract_title(soup, api_data, json_ld)
        uploader = self._extract_uploader(soup, api_data, json_ld)
        categories = self._extract_categories(soup, api_data, json_ld)
        tags = self._extract_tags(soup, api_data, json_ld)
        music = self._extract_music(soup, api_data)
        creator = self._extract_creator(soup)
        stars = self._extract_stars(soup, api_data)
        description = self._extract_description(soup, api_data, json_ld)
        duration = self._extract_duration(soup, api_data, json_ld)
        view_count = self._extract_view_count(soup, api_data, json_ld)
        like_count = api_data.get('likes')
        dislike_count = api_data.get('dislikes')
        average_rating = api_data.get('rating')
        upload_date = self._extract_upload_date(soup, api_data, json_ld)
        thumbnails = self._extract_thumbnails(soup, api_data, json_ld)
        formats = self._extract_formats(soup, url, json_ld, api_data)
        video_meta = self._extract_video_meta(soup, api_data)
        fun_scripts = self._extract_funscripts(api_data)

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
            'like_count': like_count,
            'dislike_count': dislike_count,
            'average_rating': average_rating,
            'upload_date': upload_date,
            'thumbnails': thumbnails,
            'formats': formats,
            'user_fun_scripts': fun_scripts,
            **video_meta
        }

    def _extract_json_ld_video_object(self, soup):
        """
        Traverses all application/ld+json scripts on the page to find
        and aggregate fields from a 'VideoObject' structure.
        """
        video_data = {}
        for script in soup.find_all('script', type='application/ld+json'):
            if not script.string:
                continue
            try:
                data = json.loads(script.string)

                def walk(obj):
                    if isinstance(obj, dict):
                        if obj.get('@type') == 'VideoObject':
                            for k, v in obj.items():
                                if v and k not in video_data:
                                    video_data[k] = v
                        for v in obj.values():
                            walk(v)
                    elif isinstance(obj, list):
                        for item in obj:
                            walk(item)

                walk(data)
            except Exception:
                pass
        return video_data

    def _extract_title(self, soup, api_data, json_ld):
        if api_data.get('title'):
            return api_data['title'].strip()

        if json_ld.get('name'):
            return json_ld['name'].strip()

        title_meta = soup.find('meta', attrs={'property': 'og:title'})
        if not title_meta:
            title_meta = soup.find('meta', attrs={'name': 'og:title'})
        if not title_meta:
            title_meta = soup.find('meta', attrs={'name': 'twitter:title'})

        if title_meta and title_meta.get('content'):
            raw_title = title_meta['content']
        else:
            title_tag = soup.find('title')
            raw_title = title_tag.string if title_tag else None

        if not raw_title:
            h1_tag = soup.find('h1')
            raw_title = h1_tag.get_text() if h1_tag else None

        if raw_title:
            clean_title = raw_title.strip()
            clean_title = re.sub(r'\s*-\s*PMVHaven\s*$', '', clean_title, flags=re.IGNORECASE)
            return clean_title

        return None

    def _extract_uploader(self, soup, api_data, json_ld):
        if api_data.get('uploader'):
            return api_data['uploader']
        if api_data.get('uploaderUsername'):
            return api_data['uploaderUsername']

        creator = json_ld.get('author') or json_ld.get('creator')
        if isinstance(creator, dict) and creator.get('name'):
            return creator['name']
        return None

    def _extract_categories(self, soup, api_data, json_ld):
        return []

    def _extract_tags(self, soup, api_data, json_ld):
        # 1. API Endpoint
        if api_data.get('tags') and isinstance(api_data['tags'], list):
            return [t.strip() for t in api_data['tags'] if t.strip()]

        # 2. JSON-LD Keyword string
        if json_ld.get('keywords'):
            return [k.strip() for k in json_ld['keywords'].split(',') if k.strip()]

        # 3. DOM Meta tags fallback
        tags_meta = soup.find('meta', attrs={'property': 'og:video:tag'})
        if tags_meta:
            return [t.strip() for t in tags_meta['content'].split(',') if t.strip()]
        keywords_meta = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_meta:
            return [t.strip() for t in keywords_meta['content'].split(',') if t.strip()]

        return []

    def _extract_music(self, soup, api_data):
        music_list = api_data.get('music')
        # Return exact dictionary format
        if isinstance(music_list, list):
            return music_list
        return []

    def _extract_funscripts(self, api_data):
        fun_scripts = api_data.get('userFunScripts')
        # Return exact dictionary format
        if isinstance(fun_scripts, list):
            return fun_scripts
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

    def _extract_stars(self, soup, api_data):
        stars = set()
        if api_data.get('stars') and isinstance(api_data['stars'], list):
            for s in api_data['stars']:
                if s.strip():
                    stars.add(s.strip())
        if api_data.get('starsTags') and isinstance(api_data['starsTags'], list):
            for s in api_data['starsTags']:
                if s.strip():
                    stars.add(s.strip())
        return list(stars) if stars else []

    def _extract_description(self, soup, api_data, json_ld):
        if api_data.get('description'):
            return api_data['description']

        #if json_ld.get('description'):
        #    return json_ld['description']

        #desc_meta = soup.find('meta', attrs={'name': 'description'})
        #if desc_meta:
        #    return desc_meta['content']
        #desc_meta = soup.find('meta', attrs={'property': 'og:description'})
        #if desc_meta:
        #    return desc_meta['content']
        return None

    def _extract_duration(self, soup, api_data, json_ld):
        # API provides specific duration in seconds directly
        if api_data.get('durationSeconds') is not None:
            try:
                return int(api_data['durationSeconds'])
            except ValueError:
                pass

        if api_data.get('duration'):
            try:
                # Sometimes duration is returned as '1:30', fallback logic if 'durationSeconds' misses
                duration_str = str(api_data['duration'])
                if ':' in duration_str:
                    parts = duration_str.split(':')
                    return sum(int(x) * 60 ** i for i, x in enumerate(reversed(parts)))
                return int(duration_str)
            except ValueError:
                pass

        duration_meta = soup.find('meta', attrs={'property': 'og:video:duration'})
        if duration_meta and duration_meta.get('content'):
            try:
                return int(duration_meta['content'])
            except ValueError:
                pass
        return None

    def _extract_view_count(self, soup, api_data, json_ld):
        if api_data.get('views'):
            try:
                return int(api_data['views'])
            except ValueError:
                pass

        interactions = json_ld.get('interactionStatistic')
        if isinstance(interactions, list):
            for interaction in interactions:
                i_type = interaction.get('interactionType')
                if isinstance(i_type, dict) and i_type.get('@type') == 'WatchAction':
                    return interaction.get('userInteractionCount')
                elif isinstance(i_type, str) and 'WatchAction' in i_type:
                    return interaction.get('userInteractionCount')
        return None

    def _extract_upload_date(self, soup, api_data, json_ld):
        # Check API first (releaseDate is most accurate), then fallback to JSON-LD
        date_str = api_data.get('releaseDate') or api_data.get('createdAt') or json_ld.get('uploadDate')

        if date_str:
            # Converts format "2024-01-01T00:00:00.000Z" to yt-dlp standard "20240101"
            m = re.match(r'^(\d{4})-?(\d{2})-?(\d{2})', date_str)
            if m:
                return f"{m.group(1)}{m.group(2)}{m.group(3)}"
        return None

    def _extract_thumbnails(self, soup, api_data, json_ld):
        thumbnails = []
        sizes = api_data.get('thumbnailSizes')

        # Prioritize exact multi-resolution API sizes
        if isinstance(sizes, dict):
            for size_key, size_data in sizes.items():
                if isinstance(size_data, dict) and size_data.get('url'):
                    thumbnails.append({
                        'id': size_key,
                        'url': size_data['url'],
                        'width': size_data.get('width'),
                        'height': size_data.get('height'),
                        'filesize': size_data.get('size'),
                    })

        # If individual sizes were missing or empty, fallback to basic options
        if not thumbnails:
            if api_data.get('thumbnailUrl'):
                thumbnails.append({'url': api_data['thumbnailUrl']})
            elif json_ld.get('thumbnailUrl'):
                thumbnails.append({'url': json_ld['thumbnailUrl']})
            else:
                thumbnail_meta = soup.find('meta', attrs={'property': 'og:image'})
                if not thumbnail_meta:
                    thumbnail_meta = soup.find('meta', attrs={'name': 'twitter:image'})
                if thumbnail_meta:
                    thumbnails.append({'url': thumbnail_meta['content']})

        return thumbnails

    def _extract_formats(self, soup, url, json_ld, api_data):
        webpage = str(soup)

        title_meta = soup.find('title')
        title = title_meta.string if title_meta else ''
        title_norm = re.sub(r'\s+', ' ', title).strip().lower()

        page_vid = self._search_regex(
            r'_([0-9a-fA-F]{24})', url, 'video id', default=None)

        slug = None
        m_slug = re.search(r'/video/([^_?]+)_[0-9a-fA-F]{24}', url)
        if m_slug:
            slug = urllib.parse.unquote(m_slug.group(1))
        slug_words = [w.lower() for w in re.split(r'[-_\s]+', slug or '') if len(w) > 2]

        width = self._extract_width(soup, api_data)
        height = self._extract_height(soup, api_data)
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

        # 1. Gather standalone progressive MP4 links
        if api_data.get('videoUrl'):
            add_candidate(api_data['videoUrl'], base_score=50, source='api')
        if api_data.get('previewUrl'):
            add_candidate(api_data['previewUrl'], base_score=-20, source='api')

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

        # 2. Gather adaptive M3U8 (HLS) stream manifests
        m3u8_urls = set()

        if api_data.get('hlsMasterPlaylistUrl'):
            m3u8_urls.add(api_data['hlsMasterPlaylistUrl'])
        elif json_ld.get('contentUrl'):
            m3u8_urls.add(json_ld['contentUrl'])

        # Fallback regular expression scanner for raw .m3u8 assignments inside the DOM strings
        m3u8_patterns = [
            rf'https?:{_SEP}{_SEP}video\.pmvhaven\.com{_SEP}[^"\'<>\s]+?\.m3u8',
            rf'https?:{_SEP}{_SEP}storage\.pmvhaven\.com{_SEP}[^"\'<>\s]+?\.m3u8',
        ]
        for pattern in m3u8_patterns:
            for u in re.findall(pattern, webpage):
                u = u.replace('\\u002F', '/')
                m3u8_urls.add(u)

        formats = []

        # Determine if we have any valid video formats (non-preview)
        has_real_video = any(not c['is_preview'] for c in candidates) or bool(m3u8_urls)

        # Build progressive format objects
        if candidates:
            unique = {}
            for c in candidates:
                u = c['url']
                if u not in unique or c['score'] > unique[u]['score']:
                    unique[u] = c

            for idx, c in enumerate(unique.values()):
                # Omit previews entirely if we have legitimate full formats
                if has_real_video and c['is_preview']:
                    continue

                parsed_cand = urllib.parse.urlsplit(c['url'])
                subdomain = parsed_cand.netloc.split('.')[0] if parsed_cand.netloc else 'video'
                preview_suffix = '-preview' if c['is_preview'] else ''
                format_id = f'{subdomain}{preview_suffix}-{idx}'

                fmt = {
                    'url': c['url'],
                    'ext': 'mp4',
                    'format_id': format_id,
                    'http_headers': {'Referer': url},
                    'preference': c['score'],
                }

                if not c['is_preview']:
                    # API file size
                    if api_data.get('fileSize'):
                        fmt['filesize'] = api_data['fileSize']

                    if resolution:
                        fmt['resolution'] = resolution
                    if height:
                        fmt['height'] = height

                    m_h = re.search(r'(\d{3,4})p', c['url'])
                    if m_h:
                        h = int(m_h.group(1))
                        if h:
                            fmt['height'] = h
                            if h != height:
                                fmt.pop('resolution', None)
                else:
                    # Explicitly remove dimensions so previews aren't assigned the main video's size
                    fmt['format_note'] = 'Preview'
                    fmt.pop('resolution', None)
                    fmt.pop('height', None)
                    fmt.pop('width', None)

                formats.append(fmt)

        # Extract adaptive sub-formats via HLS stream extraction loops
        for m3u8_url in m3u8_urls:
            hls_formats = self._extract_m3u8_formats(
                m3u8_url, page_vid or 'video', ext='mp4',
                entry_protocol='m3u8_native', m3u8_id='hls', fatal=False
            )
            for f in hls_formats:
                f.setdefault('http_headers', {})['Referer'] = url
            formats.extend(hls_formats)

        return formats

    def _extract_video_meta(self, soup, api_data):
        meta = {}

        width = self._extract_width(soup, api_data)
        height = self._extract_height(soup, api_data)

        if width and height:
            meta['width'] = width
            meta['height'] = height
            meta['resolution'] = f"{width}x{height}"

        return meta

    def _extract_width(self, soup, api_data):
        if api_data.get('width'):
            return int(api_data['width'])

        width_meta = soup.find('meta', attrs={'property': 'og:video:width'})
        if not width_meta:
            width_meta = soup.find('meta', attrs={'name': 'twitter:player:width'})
        if width_meta:
            return int(width_meta['content'])
        return None

    def _extract_height(self, soup, api_data):
        if api_data.get('height'):
            return int(api_data['height'])

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
