#!/usr/bin/python

from BeautifulSoup import BeautifulSoup
from datetime import datetime
import sqlite3
import urllib2
import sys
import re


conn = sqlite3.connect('ign.s3db')
cursor = conn.cursor()
letters = 'abcdefghijklmnopqrstuvwxyz'
systems = [ 'x360', 'ps3', 'wii', 'pc', 'psp', 'ds' ]
dt1 = [ 'Genre:', 'Publisher:', 'Developer:' ]
dt2 = [ 'Release Date:', 'Cancelled', 'Also on:', 'Exclusively on:', 'MSRP:', 'ESRB:' ]

def parse_ign_game(id, id2, link):
	url = link #get_ign_summary_url(id2)
	try:
		html = urllib2.urlopen(url).read()
	except:
		return	
	soup = BeautifulSoup(html)
	about = soup.find(id='about-tabs-data')
	if about is not None:
		thumb = soup.find(attrs = { "class" : "img-thumb" })
		
		if thumb is not None:
			img_thumb = thumb.find('img')
            try:
                thumbnail = img_thumb['src']
            except: thumbnail = None
		else:
			thumbnail = None
			
		summary_node = about.find(attrs = { "class" : "column-about-boxart" })
		if summary_node is not None:
			summary = summary_node.text
		else:
			summary = None
		
		genre = None
		publisher = None
		developer = None

		release_date_text = None
		release_date = None
		msrp = None
		also_on = None
		esrb_rating = None
		esrb_reason = None
		
		details1 = about.find(attrs = { "class" : "column-about-details" })
		active_dt1 = None
		if details1 is not None:
			for detail1 in details1:
				if detail1 is not None:
					if not is_nav_str(detail1) and detail1.text.strip() in dt1:
						active_dt1 = dt1.index(detail1.text.strip())
					elif active_dt1 is not None and not (is_nav_str(detail1) and detail1.strip() == ""):
						if active_dt1 == 0:
							genre = (detail1.strip() if is_nav_str(detail1) else detail1.text.strip()).replace('\n', ', ')
						elif active_dt1 == 1:
							publisher = detail1.strip() if is_nav_str(detail1) else detail1.text.strip()
						elif active_dt1 == 2:
							developer = detail1.strip() if is_nav_str(detail1) else detail1.text.strip()
						active_dt1 = None	
		print "details1: \"%s\" | \"%s\" | \"%s\"" % ( genre, publisher, developer )

		details2 = about.find(attrs = { "class" : "column-about-details-2" })
		active_dt2 = None
		if details2 is not None:
			for detail2 in details2:
				if detail2 is not None:
					if not is_nav_str(detail2) and detail2.text.strip() in dt2:
						active_dt2 = dt2.index(detail2.text.strip())
					elif (not is_nav_str(detail2)) and (detail2.find('a') is not None) and (detail2.find('a')['href'] == 'http://www.ign.com/esrb.html'):
						active_dt2 = 5
						esrb_rating = detail2.find('a').text.strip()
						esrb_rating = esrb_rating[:esrb_rating.find(' ')]
					elif active_dt2 is not None and not (is_nav_str(detail2) and detail2.strip() == ""):
						if active_dt2 == 0:
							release_date_text = detail2.strip() if is_nav_str(detail2) else detail2.text.strip()
							try:
								release_date = datetime.strptime(release_date_text, '%B %d, %Y')
							except:
								release_date = None
						elif active_dt2 == 1:
							release_date_text = 'Cancelled'
						elif active_dt2 == 2:
							also_on = detail2.strip() if is_nav_str(detail2) else detail2.text.strip()
						elif active_dt2 == 3:
							also_on = None
						elif active_dt2 == 4:
							msrp = detail2.strip() if is_nav_str(detail2) else detail2.text.strip()
						elif active_dt2 == 5:
							esrb_reason = (detail2.strip() if is_nav_str(detail2) else detail2.text.strip())[2:]
						active_dt2 = None	
		print "details2: \"%s\" | \"%s\" | \"%s\"" % ( release_date_text, also_on, msrp )
	
	ign_score_node = soup.find(attrs = { "class" : "value integer" })
	if ign_score_node is not None:
		ign_score = ign_score_node.text.strip()
	else:
		ign_score = None
	
	press_score = None
	press_count = None
	reader_score = None
	reader_count = None
	score_items = soup.findAll(attrs = { "class" : "score-item" })
	if score_items is not None and len(score_items) == 2:
		press_item = score_items[0]
		if press_item is not None:
			press_score_item = press_item.find('div')
			if press_score_item is not None:
				press_score = press_score_item.text.strip()
				if not is_number(press_score): press_score = None	
			press_count_item = press_item.find('a')
			if press_count_item is not None:
				press_count = press_count_item.text.strip().replace(' ratings', '')
				if not is_number(press_count): press_count = None				
		reader_item = score_items[1]
		if reader_item is not None:
			reader_score_item = reader_item.find('div')
			if reader_score_item is not None:
				reader_score = reader_score_item.text.strip() 
				if not is_number(reader_score): reader_score = None
			reader_count_item = reader_item.find('a')
			if reader_count_item is not None:
				reader_count = reader_count_item.text.strip().replace(' ratings', '')
				if not is_number(reader_count): reader_count = None
	
	try:
		cursor.execute("INSERT INTO game_info " \
			"(id,thumbnail,summary,genre,publisher,developer,release_date_text,msrp,also_on,ign_score,press_score,press_count,reader_score,reader_count,release_date,esrb_rating,esrb_reason) " \
			"VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", \
			[id,thumbnail,summary,genre,publisher,developer,release_date_text,msrp,also_on,ign_score,press_score,press_count,reader_score,reader_count,release_date,esrb_rating,esrb_reason])
	except:
		return

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
	games = soup.findAll(attrs = { "class" : "no-pad-btm" })
	for game in games:
		listings = game.findAll(attrs = { "class" : "listings first" })
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
		
		try:
			cursor.execute("INSERT INTO game " \
				"(id,id1,id2,name,link,rating,system,last_updated) "\
				"VALUES (?,?,?,?,?,?,?,?)", \
				[ id, id1, id2, name, link, rating, system, last_updated ])
		except:
			return
			
		parse_ign_game(id, id2, link)	
		
		conn.commit()
		
def get_ign_url(system, letterNum):
	letter = 'other' if letterNum >= len(letters) else letters[letterNum]
	return "http://www.ign.com/_views/ign/ign_tinc_games_by_platform.ftl" \
			"?platform=%s&sort=title&order=asc&max=50000&sortOrders=axxx&catalogLetter=%s" % (system, letter) 

def get_ign_summary_url(id2):
	return "http://www.ign.com/_views/ign/ign_tinc_game_about.ftl?id=%s&network=12&js_tab=summary&locale=us" % id2
			
parse_ign_all()
cursor.close()




			# d1str = details1.text.replace('Genre:', '~Genre:') \
				# .replace('Publisher:', '~Publisher:') \
				# .replace('Developer:', '~Developer:')
			##Genre:StrategyPublisher:MicrosoftDeveloper:TBA
			# match1 = re.search('(~Genre:(?P<genre>[^~]+))*(~Publisher:(?P<publisher>[^~]+))*(~Developer:(?P<developer>[^~]+))*', d1str)
			# if match1:
				# genre = match1.group('genre')
				# publisher = match1.group('publisher')
				# developer = match1.group('developer')
				# print "%s | %s | %s" % ( genre, publisher, developer )
			# else:
				# no_details1()
				
				
				
			# d2str = details2.text.replace('Cancelled', '~Release Date:Cancelled') \
				# .replace('Release Date:', '~Release Date:') \
				# .replace('Exclusively on:', '~Also on:N/A') \
				# .replace('Also on:', '~Also on:')
			##Release Date:TBAExclusively on:Xbox 360
			# match2 = re.search('(~Release Date:(?P<rdate>[^~]+))*(~Also on:(?P<also_on>[^~]+))*', d2str)
			# if match2:
				# release_date_text = match2.group('rdate')
				# also_on = match2.group('also_on')
				# print "%s | %s" % ( release_date_text, also_on )
			# else:
				# no_details2()
	