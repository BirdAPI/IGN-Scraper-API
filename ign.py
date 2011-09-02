#!/usr/bin/python

from BeautifulSoup import BeautifulSoup
from datetime import datetime
import sqlite3
import urllib2
import sys
import re
import shutil

__author__ = "Anthony Casagrande <birdapi@gmail.com>"
__version__ = "0.4"

DATABASE_FILENAME = 'ign.s3db'
DATABASE_SCHEMA_FILENAME = 'ign.schema.s3db'
LETTERS = 'abcdefghijklmnopqrstuvwxyz'
SYSTEMS = [ 'x360', 'ps3', 'wii', 'pc', 'psp', 'ds' ]

class Game:
    def __init__(self):
        self.id = None
        self.id1 = None
        self.id2 = None
        self.subdomain = None
        self.name = None
        self.link = None
        self.rating = None
        self.system = None
        self.last_updated = None
    
    @staticmethod    
    def get_insert_string(table_name = "game"):
        return "INSERT INTO %s (id,id1,id2,subdomain,name,link,rating,system,last_updated) VALUES (?,?,?,?,?,?,?,?,?)" % table_name
    
    def get_insert_values(self):
        return [ self.id, self.id1, self.id2, self.subdomain, self.name, self.link, self.rating, self.system, self.last_updated ]

    def insert_into_db(self, filename, table_name = "game"):
        conn = sqlite3.connect(filename)
        cursor = conn.cursor()
        try:
            cursor.execute(Game.get_insert_string(table_name), self.get_insert_values())
        except:
            print "Error inserting game row into database:\n\t%s" % (self.get_insert_values())
        finally:
            conn.commit()
            cursor.close()        
        
    def __repr__(self):
        return repr(self.get_insert_values())
        
class GameInfo:
    def __init__(self):
        self.id = None
        self.name = None
        self.system = None
        self.link = None
        self.thumbnail = None
        self.summary = None
        self.genre = None
        self.publisher = None
        self.developer = None
        self.release_date_text = None
        self.msrp = None
        self.also_on = None
        self.ign_score = None
        self.press_score = None
        self.press_count = None
        self.reader_score = None
        self.reader_count = None
        self.release_date = None
        self.esrb_rating = None
        self.esrb_reason = None
        
    @staticmethod    
    def get_insert_string(table_name = "game_info"):
        return "INSERT INTO %s " \
                "(id,name,system,link,thumbnail,summary,genre,publisher,developer,release_date_text," \
                "msrp,also_on,ign_score,press_score,press_count,reader_score,reader_count," \
                "release_date,esrb_rating,esrb_reason) " \
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)" % table_name
    
    def get_insert_values(self):
        return [ self.id, self.name, self.system, self.link, self.thumbnail, self.summary, self.genre, self.publisher, self.developer, self.release_date_text, self.msrp, self.also_on, self.ign_score, self.press_score, self.press_count, self.reader_score, self.reader_count, self.release_date, self.esrb_rating, self.esrb_reason ]

    def insert_into_db(self, filename, table_name = "game_info"):
        conn = sqlite3.connect(filename)
        cursor = conn.cursor()
        try:
            cursor.execute(GameInfo.get_insert_string(table_name), self.get_insert_values())
        except:
            print "Error inserting game info row into database:\n\t%s" % (self.get_insert_values())
        finally:
            conn.commit()
            cursor.close()

    def __repr__(self):
        return repr(self.get_insert_values())            
        
class SearchResult:
    def __init__(self):
        self.title = None
        self.system = None
        self.score = None
        self.boxart = None
        self.description = None
        self.link = None      
        
    def __repr__(self):
        return repr([ self.title, self.system, self.score, self.boxart, self.description, self.link ])

"""
Class that contains all of the public API functions
"""
class IGN:
    """
    Returns a list of Game objects that are returned from
    performing a search on ign, or None if no games are found. 
    """
    @staticmethod
    def search(search):
        url = get_ign_search_url(search)
        try:
            xml = urllib2.urlopen(url).read()
        except: 
            return None
        soup = BeautifulSoup(xml)
        docs = soup.findAll('doc')
        results = []
        for doc in docs:
            result = SearchResult()
            result.title = get_ign_value(doc, "title")
            result.system = get_ign_value(doc, "platformName")
            result.score = get_ign_value(doc, "objectScoreNumeric")
            result.boxart = get_ign_value(doc, "boxArt")
            result.description = get_ign_value(doc, "description")
            result.link = get_ign_value(doc, "url")
            results.append(result)
        return results

    @staticmethod
    def get_info(game):    
        return IGN.get_game_info(game.link)
        
    @staticmethod
    def get_game_info(link, max_retries = 5, retry_count = 0):
        info = GameInfo()
        info.id = IGN.get_id(link)
        info.link = link
        try:
            html = get_html(link)
        except: 
            return None  
        soup = BeautifulSoup(html)
        
        title = soup.find("title")
        if not title or title.text == "IGN Advertisement":
            if retry_count < max_retries:
                print "Retry %i of %i: %s" % (retry_count + 1, max_retries, link)
                return IGN.get_game_info(link, max_retries, retry_count + 1)
            else:
                return None
        
        game_title = soup.find("a", attrs ={"class":"game-title"})
        if game_title:
            nav_platform = game_title.find("span", attrs={"class":"nav-platform"})
            if nav_platform:
                info.system = nav_platform.text.strip()
                info.name = game_title.text.replace(info.system, "").strip()
        
        txt_tagline = soup.find("div", attrs={"class":"txt-tagline"})
        if txt_tagline:
            info.release_date_text = txt_tagline.text.strip()
            try:
                info.release_date = datetime.strptime(info.release_date_text, '%B %d, %Y')
            except:
                info.release_date = None
        
        about = soup.find(id='about-tabs-data')
        if about is not None:
            thumb = soup.find(attrs = { "class" : "img-thumb" })
            
            if thumb is not None:
                img_thumb = thumb.find('img')
                try:
                    info.thumbnail = img_thumb['src']
                except KeyError: 
                    info.thumbnail = None
            
            details1 = about.find(attrs = { "class" : "column-about-details" })
            parse_details1(details1, info)

            details2 = about.find(attrs = { "class" : "column-about-details-2" })
            parse_details2(details2, info)
            
            summary_node = about.find(attrs = { "class" : "column-about-boxart" })
            if summary_node is not None:
                summary = summary_node.text
                if details1 is not None:
                    summary = summary[:summary.find(details1.text)]
                elif details2 is not None:
                    summary = summary[:summary.find(details1.text)]
                info.summary = summary.strip()             
        
        ign_score_node = soup.find(attrs = { "class" : "value integer" })
        if ign_score_node is not None:
            info.ign_score = ign_score_node.text.strip()
        
        score_items = soup.findAll(attrs = { "class" : "score-item" })
        parse_score_items(score_items, info)
        
        return info
    
    """
    Returns a list of Game objects returned by a
    scrape of a game list page for a certain
    system and letter. 
    """
    @staticmethod
    def parse_page(system, letterNum):
        url = get_ign_url(system, letterNum)
        print url
        try:
            html = urllib2.urlopen(url).read()
        except:
            print "Error reading url: %s" % (url)
            return None
        soup = BeautifulSoup(html)
        gs = soup.findAll(attrs = { "class" : "no-pad-btm" })
        games = []
        for g in gs:
            game = Game()
            listings = g.findAll(attrs = { "class" : "listings first" })
            name_node = listings[0]
            a_name = name_node.find('a')
            rating_node = listings[1]
            h3_rating = rating_node.find('h3')
            update_node = listings[2]
            h3_update = update_node.find('h3')
            
            game.name = a_name.text
            game.link = a_name['href']
            tokens = game.link.split('/')
            game.subdomain = tokens[2][ : tokens[2].find('.')]
            game.id1 = tokens[4]
            game.id2 = tokens[5].replace('.html', '')
            game.id = game.id1 + "_" + game.id2 + "_" + game.subdomain
            game.rating = h3_rating.text
            if game.rating == 'NR':
                game.rating = None
            update = h3_update.text
            if update == '':
                game.last_updated = None
            else:
                game.last_updated = datetime.strptime(update, '%b %d, %Y')
            
            games.append(game)
        return games
           
    @staticmethod
    def parse_system(system):
        for i in range(len(LETTERS) + 1):
            games = IGN.parse_page(system, i)
            infos = {}
            for game in games:
                info = IGN.get_game_info(game)
                if info is None:
                    info = IGN.get_game_info(result.link)
                infos[game.id] = info
                print info

    @staticmethod
    def parse_all():
        for system in SYSTEMS:
            IGN.parse_system(system)
            
    """
    Returns (id, id1, id2) from any given
    ign game link.
    """
    @staticmethod
    def get_ids(link):
        match = re.search("http://(?P<subdomain>.+).ign.com/objects/(?P<id1>[^/]+)/(?P<id2>[^\.]+).html", link)
        if match:
            id1 = match.group("id1").strip()
            id2 = match.group("id2").strip()
            subdomain = match.group("subdomain")
            return ("%s_%s_%s" % (id1, id2, subdomain), id1, id2, subdomain)
        else:
            return (None, None, None, None)

    """
    Given and id in the format id1_id2_subdomain, return (id1, id2, subdomain)
    """
    @staticmethod
    def split_id(id):
        tokens = id.split('_')
        if len(tokens) == 3:
            return (tokens[0], tokens[1], tokens[2])
        else:
            return (None, None, None)
        
    """
    Returns the combined id from any given
    ign game link.
    """
    @staticmethod
    def get_id(link):
        (id, id1, id2, subdomain) = IGN.get_ids(link)
        return id
        
    @staticmethod
    def get_info_link(id):
        (id1, id2, subdomain) = IGN.split_id(id)
        return "http://%s.ign.com/objects/%s/%s.html" % (subdomain, id1, id2)
            
    @staticmethod
    def copy_blank_db(filename):
        try:
            shutil.copy(DATABASE_SCHEMA_FILENAME, filename)
        except IOError:
            print "Error copying %s to %s" % (DATABASE_SCHEMA_FILENAME, filename)

def get_ign_value(doc, name):
    try:
        return doc.find(attrs = { "name" : name }).text.strip()
    except: 
        return None
            
def parse_details1(details1, info):
    dt1 = [ 'Genre:', 'Publisher:', 'Developer:' ]
    active_dt1 = None
    if details1 is not None:
        for detail1 in details1:
            if detail1 is not None:
                if not is_nav_str(detail1) and detail1.text.strip() in dt1:
                    active_dt1 = dt1.index(detail1.text.strip())
                elif active_dt1 is not None and not (is_nav_str(detail1) and detail1.strip() == ""):
                    if active_dt1 == 0:
                        info.genre = (detail1.strip() if is_nav_str(detail1) else detail1.text.strip()).replace('\n', ', ')
                    elif active_dt1 == 1:
                        info.publisher = detail1.strip() if is_nav_str(detail1) else detail1.text.strip()
                    elif active_dt1 == 2:
                        info.developer = detail1.strip() if is_nav_str(detail1) else detail1.text.strip()
                    active_dt1 = None    
    #print "details1: \"%s\" | \"%s\" | \"%s\"" % ( info.genre, info.publisher, info.developer )    

def parse_details2(details2, info):
    dt2 = [ 'Release Date:', 'Cancelled', 'Also on:', 'Exclusively on:', 'MSRP:', 'ESRB:' ]
    active_dt2 = None
    if details2 is not None:
        for detail2 in details2:
            if detail2 is not None:
                if not is_nav_str(detail2) and detail2.text.strip() in dt2:
                    active_dt2 = dt2.index(detail2.text.strip())
                elif (not is_nav_str(detail2)) and (detail2.find('a') is not None) and (detail2.find('a')['href'] == 'http://www.ign.com/esrb.html'):
                    active_dt2 = 5
                    esrb_rating = detail2.find('a').text.strip()
                    info.esrb_rating = esrb_rating[:esrb_rating.find(' ')]
                elif active_dt2 is not None and not (is_nav_str(detail2) and detail2.strip() == ""):
                    if active_dt2 == 0:
                        info.release_date_text = detail2.strip() if is_nav_str(detail2) else detail2.text.strip()
                        try:
                            info.release_date = datetime.strptime(info.release_date_text, '%B %d, %Y')
                        except:
                            info.release_date = None
                    elif active_dt2 == 1:
                        info.release_date_text = 'Cancelled'
                    elif active_dt2 == 2:
                        info.also_on = detail2.strip() if is_nav_str(detail2) else detail2.text.strip()
                    elif active_dt2 == 3:
                        info.also_on = None
                    elif active_dt2 == 4:
                        info.msrp = detail2.strip() if is_nav_str(detail2) else detail2.text.strip()
                    elif active_dt2 == 5:
                        info.esrb_reason = (detail2.strip() if is_nav_str(detail2) else detail2.text.strip())[2:]
                    active_dt2 = None    
    #print "details2: \"%s\" | \"%s\" | \"%s\"" % ( info.release_date_text, info.also_on, info.msrp )    
    
def parse_score_items(score_items, info):
    if score_items is not None and len(score_items) == 2:
        press_item = score_items[0]
        if press_item is not None:
            press_score_item = press_item.find('div')
            if press_score_item is not None:
                info.press_score = press_score_item.text.strip()
                if not is_number(info.press_score): info.press_score = None    
            press_count_item = press_item.find('a')
            if press_count_item is not None:
                info.press_count = press_count_item.text.strip().replace(' ratings', '')
                if not is_number(info.press_count): info.press_count = None                
        reader_item = score_items[1]
        if reader_item is not None:
            reader_score_item = reader_item.find('div')
            if reader_score_item is not None:
                info.reader_score = reader_score_item.text.strip() 
                if not is_number(info.reader_score): info.reader_score = None
            reader_count_item = reader_item.find('a')
            if reader_count_item is not None:
                info.reader_count = reader_count_item.text.strip().replace(' ratings', '')
                if not is_number(info.reader_count): info.reader_count = None    
    
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False        
        
def is_nav_str(var):
    return var.__class__.__name__ == 'NavigableString'
        
def get_ign_url(system, letterNum):
    letter = 'other' if letterNum >= len(LETTERS) else LETTERS[letterNum]
    return "http://www.ign.com/_views/ign/ign_tinc_games_by_platform.ftl" \
            "?platform=%s&sort=title&order=asc&max=50000&sortOrders=axxx&catalogLetter=%s" % (system, letter) 

def get_ign_summary_url(id2):
    return "http://www.ign.com/_views/ign/ign_tinc_game_about.ftl?id=%s&network=12&js_tab=summary&locale=us" % id2

def get_ign_search_url(search, rows = 25):
    return "http://search-api.ign.com/solr/ign.media.object/select/?wt=xml&json.wrf=jsonp1312052095285&_=1312052109888&q=%s&limit=%i&timestamp=1312052109888&rows=%i&df=title&qt=timelinehandler" % (search.replace(' ', '%20'), rows, rows)

def get_html(url):
    try:
        request = urllib2.Request(url)
        request.add_header("User-Agent", "Mozilla/5.001 (windows; U; NT4.0; en-US; rv:1.0) Gecko/25250101")
        html = urllib2.urlopen(request).read()
        return html
    except:
        print "Error accessing:", url
        return None     
    
def test_parse_page():
    IGN.copy_blank_db(DATABASE_FILENAME)
    games = IGN.parse_page('x360', 0)
    for game in games:
        if game is not None:
            print game
            print ""
            game.insert_into_db(DATABASE_FILENAME)
    infos = {}
    for game in games:
        if game is not None:
            info = IGN.get_info(game)
            if info is not None:
                info.insert_into_db(DATABASE_FILENAME)
                infos[game.id] = info
                print info
                print ""

def test_search(query, get_infos):
    results = IGN.search(query)
    for result in results:
        if result is not None:
            print result
            print ""
            if get_infos:
                info = IGN.get_game_info(result.link)
                if info is None:
                    info = IGN.get_game_info(result.link)
                print info
                print ""
                
def main():
    print "__main__"
    test_search("Call of duty", False)
    test_parse_page()


if __name__ == "__main__":
    main()
