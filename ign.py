#!/usr/bin/python

from BeautifulSoup import BeautifulSoup
from datetime import datetime
import sqlite3
import urllib2
import sys
import re
import shutil


DATABASE_FILENAME = 'ign.s3db'
DATABASE_SCHEMA_FILENAME = 'ign.schema.s3db'
letters = 'abcdefghijklmnopqrstuvwxyz'
systems = [ 'x360', 'ps3', 'wii', 'pc', 'psp', 'ds' ]

class Game:
    def __init__(self):
        self.id = None
        self.id1 = None
        self.id2 = None
        self.name = None
        self.link = None
        self.rating = None
        self.system = None
        self.last_updated = None
    
    @staticmethod    
    def get_insert_string():
        return "INSERT INTO game (id,id1,id2,name,link,rating,system,last_updated) VALUES (?,?,?,?,?,?,?,?)"
    
    def get_insert_values(self):
        return [ self.id, self.id1, self.id2, self.name, self.link, self.rating, self.system, self.last_updated ]

    def __repr__(self):
        return "%s | %s | %s | %s | %s | %s | %s" % (self.system, self.rating, self.update, self.name, self.id1, self.id2, self.id)
        
class GameInfo:
    def __init__(self):
        self.id = None
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
    def get_insert_string():
        return "INSERT INTO game_info " \
                "(id,thumbnail,summary,genre,publisher,developer,release_date_text," \
                "msrp,also_on,ign_score,press_score,press_count,reader_score,reader_count," \
                "release_date,esrb_rating,esrb_reason) " \
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    
    def get_insert_values(self):
        [ self.id, self.thumbnail, self.summary, self.genre, self.publisher, self.developer, self.release_date_text, \
            self.msrp, self.also_on, self.ign_score, self.press_score, self.press_count, self.reader_score, self.reader_count, \
            self.release_date, self.esrb_rating, self.esrb_reason ]
        
def get_ign_value(doc, name):
    try:
        return doc.find(attrs = { "name" : name }).text.strip()
    except: return None
    
def search_ign(search):
    url = get_ign_search_url(search)
    try:
        xml = urllib2.urlopen(url).read()
    except: return
    soup = BeautifulSoup(xml)
    docs = soup.findAll('doc')
    for doc in docs:
        title = get_ign_value(doc, "title")
        system = get_ign_value(doc, "platformName")
        score = get_ign_value(doc, "objectScoreNumeric")
        boxart = get_ign_value(doc, "boxArt")
        description = get_ign_value(doc, "description")
        link = get_ign_value(doc, "url")
        print "%s | %s | %s | %s | %s" % ( title, system, score, boxart, link )

def parse_ign_game_info(game):
    info = GameInfo()
    url = game.link #get_ign_summary_url(id2)
    try:
        html = urllib2.urlopen(url).read()
    except: return    
    soup = BeautifulSoup(html)
    about = soup.find(id='about-tabs-data')
    if about is not None:
        thumb = soup.find(attrs = { "class" : "img-thumb" })
        
        if thumb is not None:
            img_thumb = thumb.find('img')
            try:
                info.thumbnail = img_thumb['src']
            except KeyError: 
                info.thumbnail = None
            
        summary_node = about.find(attrs = { "class" : "column-about-boxart" })
        if summary_node is not None:
            info.summary = summary_node.text
        
        details1 = about.find(attrs = { "class" : "column-about-details" })
        parse_details1(details1, info)

        details2 = about.find(attrs = { "class" : "column-about-details-2" })
        parse_details2(details2, info)
    
    ign_score_node = soup.find(attrs = { "class" : "value integer" })
    if ign_score_node is not None:
        info.ign_score = ign_score_node.text.strip()
    
    score_items = soup.findAll(attrs = { "class" : "score-item" })
    parse_score_items(score_items, info)
    
    return info

def parse_details1(details1, game_info):
    info = game_info
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
    print "details1: \"%s\" | \"%s\" | \"%s\"" % ( info.genre, info.publisher, info.developer )    

def parse_details2(details2, game_info):
    info = game_info
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
                            info.release_date = datetime.strptime(release_date_text, '%B %d, %Y')
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
    print "details2: \"%s\" | \"%s\" | \"%s\"" % ( info.release_date_text, info.also_on, info.msrp )    
    
def parse_score_items(score_items, game_info):
    info = game_info
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
    
def parse_ign_all():
    for system in systems:
        parse_ign_system(system)

def parse_ign_system(system):
    for i in range(len(letters) + 1):
        parse_ign_page(system, i)

def parse_ign_page(system, letterNum):
    url = get_ign_url(system, letterNum)
    print url
    try:
        html = urllib2.urlopen(url).read()
    except:
        return
    soup = BeautifulSoup(html)
    gs = soup.findAll(attrs = { "class" : "no-pad-btm" })
    for g in gs:
        listings = g.findAll(attrs = { "class" : "listings first" })
        name_node = listings[0]
        a_name = name_node.find('a')
        rating_node = listings[1]
        h3_rating = rating_node.find('h3')
        update_node = listings[2]
        h3_update = update_node.find('h3')
        
        name = a_name.text
        link = a_name['href']
        tokens = link.split('/')
        id1 = tokens[4]
        id2 = tokens[5].replace('.html', '')
        id = id1 + id2
        rating = h3_rating.text
        if rating == 'NR':
            rating = None
        update = h3_update.text
        if update == '':
            last_updated = None
        else:
            last_updated = datetime.strptime(update, '%b %d, %Y')
        
        print "%s | %s | %s | %s | %s | %s | %s" % (system, rating, update, name, id1, id2, id)
        
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO game " \
                "(id,id1,id2,name,link,rating,system,last_updated) "\
                "VALUES (?,?,?,?,?,?,?,?)", \
                [ id, id1, id2, name, link, rating, system, last_updated ])
        except:
            print "Error inserting game row into database"
            return
        conn.commit()
        cursor.close()
        
        game_info = parse_ign_game_info(game)
        
        conn2 = sqlite3.connect(DATABASE_FILENAME)
        cursor2 = conn2.cursor()
        try:
            cursor2.execute(GameInfo.get_insert_string(), info.get_insert_values())
        except:
            print "Error inserting game_info row into database"
        conn2.commit()
        cursor2.close()        
        
def get_ign_url(system, letterNum):
    letter = 'other' if letterNum >= len(letters) else letters[letterNum]
    return "http://www.ign.com/_views/ign/ign_tinc_games_by_platform.ftl" \
            "?platform=%s&sort=title&order=asc&max=50000&sortOrders=axxx&catalogLetter=%s" % (system, letter) 

def get_ign_summary_url(id2):
    return "http://www.ign.com/_views/ign/ign_tinc_game_about.ftl?id=%s&network=12&js_tab=summary&locale=us" % id2

def get_ign_search_url(search):
    return "http://search-api.ign.com/solr/ign.media.object/select/?wt=xml&json.wrf=jsonp1312052095285&_=1312052109888&q=%s&limit=10&timestamp=1312052109888&rows=5&df=title&qt=timelinehandler" % search.replace(' ', '%20')

def copy_blank_db():
    try:
        shutil.copy(DATABASE_SCHEMA_FILENAME, DATABASE_FILENAME)
    except IOError:
        print "Error copying %s" % DATABASE_SCHEMA_FILENAME
        
def main():
    copy_blank_db()
    parse_ign_all()
    #search_ign('catherine')

if __name__ == "__main__":
    main()
