import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import datetime
import pytz
import os
from dotenv import load_dotenv
import json
import aiomysql


load_dotenv()

class airlineData():
    def __init__(self, username, password, pool):
        self.p = async_playwright()
        self.user = username
        self.password = password
        self.pool = pool


    async def login(self):
        self.playwright = await self.p.start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        page = self.page
        await page.goto("https://tycoon.airlines-manager.com/login")
        await page.fill("input#username", self.user)
        await page.fill("input#password", self.password)
        await page.click("button[type=submit]")
        #await page.is_visible('div.cc-window')
        #await page.click('div.cc-window .cc-btn')

    async def logout(self):
        page = self.page
        await page.goto("https://tycoon.airlines-manager.com/logout")
        await self.browser.close()
        await self.playwright.stop()
    
    async def get_country_values(self):
        page = await self.context.new_page()
        await page.goto("https://tycoon.airlines-manager.com/welcome/3?instantGame=1")
        html = await page.inner_html('div#pageContent')
        await page.close()
        soup = BeautifulSoup(html, 'html.parser')
        options = soup.find('select', {'id':'countryPicker'}).find_all('option')
        origcc = {"150": "Europe",
          "142": "Asia",
          "002": "Africa",
          "021": "North America",
          "005": "South America",
          "009": "Oceania"
         }
        values = [option['value'] for option in options[1:] if len(option['value']) == 2]
        countries = [option.text.split(' (')[0] for option in options[1:] if len(option['value']) == 2]
        continents = [origcc[option['data-continentcode']] for option in options[1:] if len(option['value']) == 2]
        async with await self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("DROP TABLE IF EXISTS country_info")
                await cursor.execute("CREATE TABLE IF NOT EXISTS country_info (country_name TEXT PRIMARY KEY, country_code TEXT, country_continent TEXT)")
                async for a,b,c in zip(values, countries, continents):
                    await cursor.execute("INSERT INTO country_info (country_name, country_code, country_continent) VALUES (%s, %s, %s) ON CONFLICT (country_name) DO UPDATE SET (country_code, country_continent) = (excluded.country_code, excluded.country_continent)", (b, a, c))
                await cursor.close()
            



    async def get_country_audit(self, val, cname, cont):
        page = await self.context.new_page()
        await page.goto("https://tycoon.airlines-manager.com/welcome/3?instantGame=1")
        await page.select('select#countryPicker', val)
        await page.click('input#submitNewTutorial')
        html = await page.is_visible('div#pageContent').inner_html('div#pageContent')
        await page.close()
        soup = BeautifulSoup(html, 'html.parser')
        hubs = soup.find_all('div', {'class':'hubListBox'})
        if len(hubs) == 0:
            return None
        country_data= []
        for hub in hubs:
            category = int(hub['data-category'])
            price = int(hub['data-price'])
            country_name = cname
            continent = cont
            name = hub.find('div', {'class':'hubNameBox'}).text.split(' ')[1]
            aptax = int(hub.find_all('p')[1].text.replace(",", "").replace(" $", "").replace("/flight", "").split(" : ")[1])
            economy, business, first = [float(dem['style'][7:].replace("%;", "")) for dem in hub.find_all('div', {'class':'barDemandFill'})]
            total = economy + 2*business + 4*first
            country_data.append((name, country_name, continent, category, economy, business, first, total, price, aptax))
        return country_data

    async def get_country_data(self):
        async with await self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM country_info")
                country_info = await cursor.fetchall()
                await cursor.close()
        return country_info




    async def get_data(self):
        await self.login()
        await self.get_country_values()
        country_info = await self.get_country_data()
        try:
            async with asyncio.TaskGroup() as tg:
                tasks = [tg.create_task(self.get_country_audit(country[1], country[0], country[2])) for country in country_info]
        except Exception as e:
            print(e)
        finally:
            await self.logout()

        hub_data = []
        for task in tasks:
            if task.result() is not None:
                hub_data.extend(task.result())
            else:
                continue

        async with await self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("CREATE TABLE IF NOT EXISTS hub_audit (airport TEXT PRIMARY KEY, country TEXT, continent TEXT, category INT, economy FLOAT, business FLOAT, first FLOAT, total FLOAT, price BIGINT, tax FLOAT)")
                await conn.commit()
                records_list_template = ','.join(['%s'] * len(hub_data))
                query = "INSERT INTO hub_audit (airport, country, continent, category, economy, business, first, total, price, tax) VALUES {} ON CONFLICT (airport) DO UPDATE SET (category, economy, business, first, total, price, tax) = (excluded.category, excluded.economy, excluded.business, excluded.first, excluded.total, excluded.price, excluded.tax)".format(records_list_template)
                await cursor.execute(query, hub_data)
                await conn.commit()
                await cursor.close()
  
        
        
async def get_pool():
    dsn = 'dbname={} user={} password={} host={}'.format(os.getenv('DBNAME'), os.getenv('DBUSER'), os.getenv('DBPASS'), os.getenv('DBHOST'))
    pool = await aiomysql.create_pool(host=os.getenv('DBHOST'), port=int(os.getenv('DBPORT')),
                                      user=os.getenv('DBUSER'), password=os.getenv('DBPASS'),
                                      db='railway')
    return pool

pool = asyncio.run(get_pool())
asyncio.run(airlineData(os.getenv('USERAUDIT'), os.getenv('PASSAUDIT'), pool).get_data())