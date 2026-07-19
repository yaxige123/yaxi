import sys
import os
import re
import json
import hashlib
import base64
import urllib.parse
import tempfile
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "黄豆短剧"
    
    def init(self, extend=""):
        self.host = "https://hdmgdj.com"
    
    def getDependence(self):
        return ["bs4"]
    
    def header(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 14; ALN-AL00 Build/HUAWEIALN-AL00) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/130.0.6723.86 Mobile Safari/537.36',
            'Referer': self.host + '/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
    
    def build_full_url(self, url):
        if not url or not isinstance(url, str):
            return ''
        url = url.strip()
        if url.startswith('http://') or url.startswith('https://'):
            return url
        if not url or url in ['null', 'undefined', '']:
            return ''
        if url.startswith('//'):
            return 'https:' + url
        if url.startswith('/'):
            return self.host + url
        if url.startswith('./'):
            return self.host + url[1:]
        return self.host + '/' + url

    def process_drama_list(self, dramas, limit=None):
        results = []
        target_dramas = dramas[:limit] if limit else dramas
        for d in target_dramas:
            remark = str(d.get("plays", ""))
            if d.get("serial"):
                remark += f" | {d.get('serial')}"
            
            results.append({
                "vod_id": str(d.get("id", "")),
                "vod_name": d.get("t", ""),
                "vod_pic": "",
                "vod_remarks": remark.strip()
            })
        return results

    def homeContent(self, filter):
        result = {"class": [], "filters": {}, "list": []}
        try:
            url = f"{self.host}/api/channel/home?platform=mobile&size=20"
            rsp = self.fetch(url, headers=self.header())
            data = json.loads(rsp.text)
            
            if data.get("code") == 0:
                tabs = data.get("data", {}).get("tabs", [])
                for tab in tabs:
                    result["class"].append({"type_id": str(tab.get("l2Id", "")), "type_name": tab.get("name", "")})
        except Exception:
            pass
        return result
    
    def homeVideoContent(self):
        try:
            url = f"{self.host}/api/channel/home?platform=mobile&size=20"
            rsp = self.fetch(url, headers=self.header())
            data = json.loads(rsp.text)
            list_data = []
            if data.get("code") == 0:
                sections = data.get("data", {}).get("sections", [])
                for sec in sections:
                    list_data.extend(sec.get("dramas", []))
                    if len(list_data) >= 30:
                        break
            return {"list": self.process_drama_list(list_data, 30)}
        except Exception:
            return {"list": []}
    
    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": pg, "pagecount": 999, "limit": 20, "total": 9999}
        try:
            home_url = f"{self.host}/api/channel/home?platform=mobile&size=20"
            home_rsp = self.fetch(home_url, headers=self.header())
            home_data = json.loads(home_rsp.text).get("data", {})
            
            target_l3Id = None
            for sec in home_data.get("sections", []):
                if str(sec.get("l2Id")) == str(tid):
                    target_l3Id = sec.get("l3Id")
                    break
            
            if target_l3Id:
                url = f"{self.host}/api/dramas?l3Id={target_l3Id}&page={pg}&size=20&sort=%E6%9C%80%E6%96%B0&platform=mobile"
            else:
                url = f"{self.host}/api/dramas?l2Id={tid}&page={pg}&size=20&sort=%E6%9C%80%E6%96%B0&platform=mobile"
                
            rsp = self.fetch(url, headers=self.header())
            data = json.loads(rsp.text)
            if data.get("code") == 0:
                dramas = data.get("data", {}).get("list", [])
                result["list"] = self.process_drama_list(dramas)
        except Exception:
            pass
        return result
    
    def detailContent(self, ids):
        result = {"list": []}
        try:
            vod_id = ids[0]
            url = f"{self.host}/api/dramas/{vod_id}?platform=mobile"
            rsp = self.fetch(url, headers=self.header())
            data = json.loads(rsp.text)
            
            if data.get("code") == 0:
                d = data.get("data", {})
                lines = []
                try:
                    ep1_rsp = self.fetch(f"{self.host}/api/dramas/{vod_id}/episodes/1?platform=mobile", headers=self.header())
                    lines = json.loads(ep1_rsp.text).get("data", {}).get("lines", [])
                except:
                    pass
                
                if not lines:
                    lines = [{"name": "默认线路", "url": ""}]
                
                vod_play_from_list = []
                vod_play_url_list = []
                
                for line in lines:
                    line_name = line.get("name", "线路")
                    line_domain = line.get("url", "")
                    vod_play_from_list.append(line_name)
                    
                    b64_domain = base64.b64encode(line_domain.encode('utf-8')).decode('utf-8')
                    ep_list = []
                    
                    if d.get("episodes"):
                        for ep in d.get("episodes"):
                            ep_num = str(ep.get("ep", ""))
                            ep_list.append(f"第{ep_num}集${vod_id}_{ep_num}_{b64_domain}")
                    else:
                        eps_count = d.get("eps", 0)
                        for i in range(1, eps_count + 1):
                            ep_list.append(f"第{i}集${vod_id}_{i}_{b64_domain}")
                            
                    vod_play_url_list.append("#".join(ep_list))
                
                result["list"].append({
                    "vod_id": str(d.get("id", vod_id)),
                    "vod_name": d.get("t", ""),
                    "vod_pic": "",
                    "vod_remarks": str(d.get("serial", "")),
                    "vod_content": str(d.get("summary", "")),
                    "vod_play_from": "$$$".join(vod_play_from_list),
                    "vod_play_url": "$$$".join(vod_play_url_list)
                })
        except Exception:
            pass
        return result
    
    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": pg, "pagecount": 999, "limit": 20, "total": 9999}
        try:
            url = f"{self.host}/api/search?kw={urllib.parse.quote(key)}&page={pg}&size=20&platform=mobile"
            rsp = self.fetch(url, headers=self.header())
            data = json.loads(rsp.text)
            if data.get("code") == 0:
                dramas = data.get("data", {}).get("list", [])
                result["list"] = self.process_drama_list(dramas)
        except Exception:
            pass
        return result
    
    def playerContent(self, flag, id, vipFlags):
        try:
            parts = id.split("_")
            if len(parts) < 2:
                return {"parse": 0, "playUrl": "", "url": "", "header": json.dumps(self.header())}
                
            drama_id = parts[0]
            ep = parts[1]
            domain = base64.b64decode(parts[2]).decode('utf-8') if len(parts) > 2 else ""
            
            rsp = self.fetch(f"{self.host}/api/dramas/{drama_id}/episodes/{ep}?platform=mobile", headers=self.header())
            data = json.loads(rsp.text)
            play_url = data.get("data", {}).get("playUrl", "")
            
            if not play_url:
                return {"parse": 0, "playUrl": "", "url": "", "header": json.dumps(self.header())}
            
            if domain:
                parsed = urllib.parse.urlparse(play_url)
                play_url = play_url.replace(f"{parsed.scheme}://{parsed.netloc}", domain.rstrip('/'))
            
            if ".m3u8" not in play_url.lower():
                return {"parse": 0, "playUrl": "", "url": play_url, "header": json.dumps(self.header())}
                
            m3u8_text = self.fetch(play_url, headers=self.header()).text
            
            hash_match = re.search(r'/hls/([0-9a-f]{64})/', play_url, re.I)
            if not hash_match:
                return {"parse": 0, "playUrl": "", "url": play_url, "header": json.dumps(self.header())}
                
            hash_str = hash_match.group(1).lower()
            ver_match = re.search(r'[?&]version=([^&#]+)', play_url)
            ver = ver_match.group(1) if ver_match else "v1"
            
            key = hashlib.md5(("xnaichanping" + hash_str + ver).encode('utf-8')).digest()
            key_b64 = base64.b64encode(key).decode('utf-8')
            
            m3u8_text = re.sub(r'URI="custom://[^"]+"', f'URI="data:application/octet-stream;base64,{key_b64}"', m3u8_text)
            
            parsed_play = urllib.parse.urlparse(play_url)
            base_path = f"{parsed_play.scheme}://{parsed_play.netloc}{parsed_play.path.rsplit('/', 1)[0]}/"
            query_str = f"?{parsed_play.query}" if parsed_play.query else ""
            
            def replace_ts(match):
                ts_path = match.group(1).strip()
                if not ts_path.startswith("http"):
                    full_ts = urllib.parse.urljoin(base_path, ts_path)
                    if query_str:
                        full_ts += "&" + query_str[1:] if "?" in full_ts else query_str
                    return full_ts
                return ts_path
                
            m3u8_text = re.sub(r'^(?!#)(?!http)(.+)$', replace_ts, m3u8_text, flags=re.MULTILINE)
            
            local_m3u8 = os.path.join(tempfile.gettempdir(), f"hdmgdj_{drama_id}_{ep}.m3u8")
            
            try:
                with open(local_m3u8, "w", encoding="utf-8") as f:
                    f.write(m3u8_text)
                final_url = f"file://{local_m3u8}"
            except Exception:
                m3u8_b64 = base64.b64encode(m3u8_text.encode('utf-8')).decode('utf-8')
                final_url = f"data:application/vnd.apple.mpegurl;base64,{m3u8_b64}"
                
            return {"parse": 0, "playUrl": "", "url": final_url, "header": json.dumps(self.header())}
        except Exception:
            return {"parse": 0, "playUrl": "", "url": "", "header": json.dumps(self.header())}
