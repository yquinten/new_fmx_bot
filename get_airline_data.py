import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import datetime
import openpyxl
import pandas as pd
import pytz
import os
from dotenv import load_dotenv
import json

load_dotenv()

class AirlinesManager():
    def __init__(self, username, password):
        self.p = async_playwright()
        self.user = username
        self.password = password
        

    async def login(self):
        self.playwright = await self.p.start()
        self.browser = await self.playwright.chromium.launch()
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        page = self.page
        await page.goto("https://tycoon.airlines-manager.com/login")
        await page.is_visible('div.cc-window')
        await page.click('div.cc-window .cc-btn')
        await page.fill("input#username", self.user)
        await page.fill("input#password", self.password)
        await page.click("button[type=submit]")
        

    async def logout(self):
        page = self.page
        await page.goto("https://tycoon.airlines-manager.com/logout")
        await self.browser.close()
        await self.playwright.stop()

    async def get_global_airline_data(self, id):
        page = await self.context.new_page()
        await page.goto(f"https://tycoon.airlines-manager.com/company/profile/airline/{str(id)}")
        html = await page.inner_html('#pageContent')
        await page.close()
        soup = BeautifulSoup(html, 'html.parser')
        member_data = []
        airline_name = soup.find('div', {'class':'companyNameBox'}).text.replace(' ', '').replace('\n', '')
        ceo_name = soup.find('div', {'class':'companyAvatars'}).find('p').find('span', {'class':'value'}).text
        print(f'{airline_name} - {ceo_name}')
        d, m, y = soup.find_all('div', {'class':'dashMachine'})[0].find('span', {'class':'bold'}).text.split('/')
        airline_creation = f'{y}-{m}-{d}'
        airline_value = soup.find_all('div', {'class':'dashMachine'})[1].find('span', {'class':'bold'}).text.replace(',', '').replace('$', '')
        offline_days = soup.find_all('div', {'class':'dashMachine'})[2].find('span', {'class':'bold'}).text.replace('Today', '0').replace('Yesterday', '1').replace(' days ago', '')
        cash_balance = soup.find_all('div', {'class':'dashMachine'})[3].find('span', {'class':'bold'}).text.replace(',', '').replace('$', '')
        print(airline_creation, offline_days, airline_value, cash_balance)
        member_data = {
            'Airline': airline_name, 
            'CEO': ceo_name, 
            'Airline Creation Date': airline_creation,
            'Airline Value': airline_value,
            'Cash Balance': cash_balance,
            'Days Since Last Login': offline_days
        }
        return member_data
    
    async def get_network_airline_data(self, id):
        page = await self.context.new_page()
        await page.goto(f"https://tycoon.airlines-manager.com/company/profile/network/{str(id)}")
        html = await page.inner_html('#pageContent')
        await page.close()
        soup = BeautifulSoup(html, 'html.parser')
        networkjson = soup.find('div', {'id': 'map_NetworkJson'}).text
        hubs = [hub['iata'] for hub in json.loads(networkjson)['airports']]
        print(hubs)
        airline_amount = soup.find_all('div', {'class':'dashMachine'})[1].find('span', {'class':'bold'}).text
        route_amount = soup.find_all('div', {'class':'dashMachine'})[2].find('span', {'class':'bold'}).text
        print(airline_amount, route_amount)
        aircraftsList={}
        aircrafts = soup.find_all('div', {'class':'aircraftBox'})
        for aircraft in aircrafts:
            aircraft_name = aircraft.find('b').text
            aircraft_amount = int(aircraft.find('span', {'class': 'aircraftCount'}).text.replace('x ', ''))
            try:
                new_amount = aircraftsList[aircraft_name]+aircraft_amount
                aircraftsList[aircraft_name]=new_amount
            except KeyError:
                aircraftsList[aircraft_name]=aircraft_amount

        aircraftsList = dict(sorted(aircraftsList.items(), key=lambda x:x[1], reverse=True))    
        member_data = {
            'Hubs': hubs,
            'Number of Hubs': len(hubs),
            'Number of Aircrafts': airline_amount,
            'Number of Routes': route_amount,
            'Aircraft Types': aircraftsList
        }
        print(member_data)
        return member_data

    async def donate(self):
        page = self.page
        await page.goto("http://tycoon.airlines-manager.com/alliance/profile")
        try:
            await page.is_visible('button.fc-cta-consent')
            await page.click('button.fc-cta-consent')
        except:
            pass
        await page.is_visible(".ui-slider-handle")
        await page.evaluate('''() => {const el = document.querySelector(".ui-slider-handle");if (el) {el.setAttribute('style', 'left: 100%;');}}''')
        #await page.eval_on_locator(".ui-slider-handle", el => el.setAttribute('style', "left: 100%;")
        #.drag_to(page.locator("generic-slider-arrow-right"))
        await page.click("button#donation-button")
        await page.is_visible("input.purchaseButton")
        await page.click("input.purchaseButton")
        


    async def get_airline_data(self):
        await self.login()
        try:
            await self.donate()
                
        except Exception as e:
            print(e)
        finally:
            await self.logout()
            
async def main():
    A = AirlinesManager("yklercq@gmail.com", "Y@nniqu311")
    await A.get_airline_data()

asyncio.run(main())




