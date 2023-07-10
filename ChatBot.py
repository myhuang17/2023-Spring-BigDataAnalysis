from flask import Flask, request, abort
from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import *#(MessageEvent, TextMessage, TextSendMessage, ImageSendMessage,ButtonsTemplate,MessageTemplateAction)
from datetime import datetime
import requests
import time
import json
from lxml import etree
import re
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18362',}
app = Flask(__name__)

line_bot_api = LineBotApi('')
handler = WebhookHandler('')
IMGUR_CLIENT_ID = ''

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    return 'OK'

#K線圖
import mplfinance as mpf
import pandas_datareader.data as web
import pyimgur
def TWplot_stcok_k_chart(IMGUR_CLIENT_ID,stock="0050"):
    """
    進行個股K線繪製，回傳至於雲端圖床的連結。將顯示包含5MA、20MA及量價關係，起始預設自2022-01-01起迄昨日收盤價。
    :stock :個股代碼(字串)，預設0050。
    :date_from :起始日(字串)，格式為YYYY-MM-DD，預設自2020-01-01起。
    """
    if int(datetime.today().strftime('%m'))<=6:
        y=int(datetime.today().strftime('%Y'))-1
    else:
        y=int(datetime.today().strftime('%Y'))
    date_from = datetime(y, 1, 1)
    stock = str(stock)+".tw"
    df = web.DataReader(stock, 'yahoo', date_from) 
    mpf.plot(df,type='candle',mav=(5,60,120),volume=True, ylabel=stock.upper()+' Price' ,savefig='testsave.png')
    PATH = "testsave.png"
    im = pyimgur.Imgur(IMGUR_CLIENT_ID)
    uploaded_image = im.upload_image(PATH, title=stock+" candlestick chart")
    return uploaded_image.link

#Lottery
res  = requests.get('http://www.taiwanlottery.com.tw/index_new.aspx')
soup = BeautifulSoup(res.text,'html.parser')
'''開獎日期 期數'''
date    = []#Announced date
periods = [] #Number of periods
for span in soup.select('span'):
	match = re.search(r'^<span class="font_black15">(.*?)\s(.*?)</span>',str(span))
	if match:
		date.append(match.group(1))
		periods.append(match.group(2))
'''special_ball 特別號'''
special_ball = []
for div in soup.select('div'):
	match = re.search(r'^<div class="ball_red">(.*?)<',str(div))
	if match:
		special_ball.append(match.group(1))
def big_lottery():
	big_lottery__order  = []
	big_lottery__sorted = []
	counter = 0
	for div in soup.select('div'):
		match = re.search(r'^<div class="ball_tx ball_yellow">(.*?)<',str(div))
		if match:
			counter += 1
			if 21 <= counter <= 26:
				big_lottery__order.append(match.group(1))
			elif 27 <= counter <= 32:
				big_lottery__sorted.append(match.group(1))
	text_1 = str(date[3]) + str(periods[3])
	text_2 = '中獎號碼:'+''.join(big_lottery__sorted)
	text_3 = '特別號碼:' + str(special_ball[2])
	result = text_1 +'\n'+ text_2 +'\n'+ text_3
	return result

#-------------------------------------------------------------------------
#分析網頁資訊 bc區塊鏈
def parse(headers,newsID):    
    fnews_url = 'https://news.cnyes.com/news/id/{}?exp=a'.format(newsID) #原始新聞網址    
    response = requests.get(fnews_url, headers)
    html=etree.HTML(response.content)   
    title=html.xpath('//*[@id="content"]/div/div/div[2]/main/div[2]/h1/text()')[0] #新聞標題
    #url=fnews_url.replace('?exp=a','')#原始新聞來源網址 
    #print(news)
    return title
def parser(y,m,d):
    #定義時間
    if m < 10:
        be_day='{}-0{}-{}'.format(y,m,d)
    else:
        be_day='{}-{}-{}'.format(y,m,d)
    #日期格式轉換成時間戳型式
    startday = int(datetime.timestamp(datetime.strptime(be_day, "%Y-%m-%d")))
    url ='https://news.cnyes.com/api/v3/news/category/tw_stock?startAt={}&endAt={}&limit=30'.format(startday,startday)
    res = requests.get(url, headers)
    newsID_lt=[]
    last_page = json.loads(res.text)['items']['last_page']
    # 篩選 newsId 值
    newsIDlist=json.loads(res.text)['items']['data']
    #獲取第一頁各個新聞的 newsId
    for i in newsIDlist:
        newsID=i['newsId']
        newsID_lt.append(newsID)
    #進行翻頁並獲取各頁面的 newsId
    for p in range(2,last_page+1):
        oth_url ='https://news.cnyes.com/api/v3/news/category/tw_stock?startAt={}&endAt={}&limit=30&page={}'.format(startday,startday,p)
        res=requests.get(oth_url, headers)
        # 獲取新聞的newsId
        newsIDlist=json.loads(res.text)['items']['data']
        for j in newsIDlist:        
            newsID=j['newsId']
            newsID_lt.append(newsID)
        #抓取每頁newsId的延遲時間
        #time.sleep(0.25)
    # 由 newsId 獲取詳細新聞內容
    final = "昨日頭條"
    for k,n in enumerate(newsID_lt):    
        data=parse(headers,n)
        final=final+"\n"+data
        #抓取每篇完整新聞的延遲時間
        #time.sleep(0)
    return final
#-------------------------------------------------------------------------


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if event.message.text[:4].upper() == "@TWK":
        input_word = event.message.text.replace(" ","") #合併字串取消空白
        stock_name = input_word[4:8] #2330
        content = TWplot_stcok_k_chart(IMGUR_CLIENT_ID,stock_name)
        message = ImageSendMessage(original_content_url=content,preview_image_url=content)
        line_bot_api.reply_message(event.reply_token, message)
    elif event.message.text == "?":
        line_bot_api.reply_message(event.reply_token,TextSendMessage("神祕小外掛 : "))
    elif event.message.text == "新聞":
        buttons_template_message = TemplateSendMessage(
            alt_text = "新聞",
            template=CarouselTemplate( 
                columns=[ 
                    CarouselColumn(
                        thumbnail_image_url='https://imgur.dcard.tw/rl7SSTZh.jpg',
                        title = "新聞", 
                        text ="請點選想查詢的新聞", 
                        actions =[
                            URITemplateAction( 
                                label="台股新聞",
                                uri= "https://news.cnyes.com/news/cat/tw_stock"),
                            URITemplateAction( 
                                label="全球股市新聞",
                                uri= "https://news.cnyes.com/news/cat/wd_stock"),
                            URITemplateAction( 
                                label="區塊鏈新聞",
                                uri= "https://news.cnyes.com/news/cat/sb")
                        ]
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template_message)
    elif event.message.text == "昨日新聞":
        #line_bot_api.reply_message(event.reply_token, TextSendMessage("請稍等"))
        beginyear=int(datetime.today().strftime('%Y'))  #爬取新聞年份
        beginmonth=int(datetime.today().strftime('%m'))    #爬取新聞開始月份
        beginday=int(datetime.today().strftime('%d'))   #爬取新聞開始日
        final = parser(beginyear,beginmonth,beginday-1)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=final))
    elif event.message.text == "大樂透":
        lott = big_lottery()
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text=lott))
    else:
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text=event.message.text))


if __name__ == "__main__":
    app.run()