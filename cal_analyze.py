
from datetime import date, datetime, timedelta, tzinfo
# import feed.date.rfc3339 as rfc
import pdb
import time as _time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from timezone import LocalTimezone
import pytz
from wordcloud import WordCloud, STOPWORDS
import random
from os import path

Local = LocalTimezone()

def get_prev_week():

    d = date.today()- timedelta(weeks = 1)

    while d.weekday() != 0:
        d = d - timedelta(days = 1)

    startTime = datetime.combine(d, datetime.min.time())
    endTime = startTime + timedelta(weeks = 1)
    return (startTime.replace(tzinfo = Local).isoformat("T"), 
        endTime.replace(tzinfo = Local).isoformat("T"))
def get_last_year():
    endTime = datetime.now(Local)
    startTime = endTime.replace(year = endTime.year-1)
    return (startTime.replace(tzinfo = Local).isoformat("T"), 
        endTime.replace(tzinfo = Local).isoformat("T"))



(startTimeDefault, endTimeDefault) = get_prev_week()

def get_events(service, calID = 'primary', startTime = startTimeDefault, 
    endTime = endTimeDefault):
    eventsResult = service.events().list(
        calendarId=calID, timeMin=startTime, timeMax = endTime, singleEvents=True,
        orderBy='startTime',maxResults = 1000).execute()
    events = eventsResult.get('items', [])
    for i in range(len(events)):
        events[i]['sourceCal'] = calID
    return events

def get_calendar_list(service):
    calendar_list = service.calendarList().list().execute()
    name2id = {}
    id2name = {}

    for calendar_list_entry in calendar_list['items']:

        key = calendar_list_entry.get('summaryOverride',calendar_list_entry.get('summary'))
        if key in name2id.keys():

            i = 2
            while key in name2id.keys():
                key = key + '_{}'.format(i)
                i = i + 1
        name2id[key] = calendar_list_entry['id']
        id2name[calendar_list_entry['id']] = key
    return name2id, id2name, calendar_list['items']
eastern = pytz.timezone('US/Eastern')
def get_event_duration(event):    
    startTime = pd.to_datetime(event['start'].get('dateTime',
        event['start'].get('date'))).tz_localize(pytz.utc).tz_convert(eastern)
    endTime = pd.to_datetime(event['end'].get('dateTime',
        event['end'].get('date'))).tz_localize(pytz.utc).tz_convert(eastern)
    dur = endTime - startTime
    if ('dateTime' in event['start']):
        allDay = False
    else:
        allDay = True
    return startTime, dur, allDay
# def rfc3339_to_datetime(dateStr):
#     Local = LocalTimezone()
#     dt = datetime.fromtimestamp(rfc.tf_from_timestamp(dateStr),Local) 
#     return dt
def gen_event_table(events, id2name):
    columns = ['StartTime','Duration','Description','Calendar','AllDay','Creator','Tags']
    lst = []
    for event in events:
        (startTime, dur,allDay) = get_event_duration(event)
        if 'sourceCal' in event.keys():
            calName = id2name[event['sourceCal']]
        else:
            calName = event['organizer']['displayName']
        eventCreator = event.get('creator').get('displayName',event['creator'].get('email'))
        eventTitle = event.get('summary','')
        lst.append([startTime, dur, eventTitle,
            calName,allDay, eventCreator,[]])

    data = pd.DataFrame(lst,columns = columns)
    data = data.set_index("StartTime")
    return data
def white_color_func(word, font_size, position, orientation, random_state=None,
 **kwargs):
    return "hsl(0, 0%%, %d%%)" % random.randint(60, 100)

def chunker(seq, size):
    return (seq[pos:pos + size] for pos in xrange(0, len(seq), size))

def get_data(service,cals_to_include = 'all'):    
    #service = get_cal_service()
    
    (name2id,id2name, calendar_list) = get_calendar_list(service)
    (startTime,endTime) = get_last_year()

    if cals_to_include is 'all':
        cals_to_include = name2id.keys()
    events = []

    for CalName in cals_to_include:
        events.extend(get_events(service,name2id[CalName],startTime,endTime))
    data = gen_event_table(events,id2name)
    data = data[(~data.AllDay)]
    return data
    # plt.figure(1)  

    # data.Duration.groupby([data.index.strftime('%Y%m'),data.Calendar]).count().plot(kind = "bar")


    # plt.ylabel("Number of events per month")
    # plt.figure(2)  
    # (data[~data.AllDay].Duration.groupby(
    #     [data[~data.AllDay].index.strftime('%Y%m'),
    #     data[~data.AllDay].Calendar]).sum() / np.timedelta64(1, 'h')).unstack(level = -1).plot(kind = "bar")
    # (data.Duration[~data.AllDay] / np.timedelta64(1, 'h')).hist()
    # plt.xlabel("Event Length (Hours)")
    # plt.ylabel("Number of events")
     


def word_cloud(data):
    text = data.Description.T.tolist()
    text = [i.encode("utf-8") for i in text]
    strs = " ".join(text)
    wc = WordCloud(width=1600, height=800,max_words=500,random_state=1).generate(strs)
    stopwords = set(STOPWORDS)
    default_colors = wc.to_array()
    plt.title("Custom colors")
    plt.imshow(wc.recolor(color_func=white_color_func, random_state=3),
    interpolation="bilinear")
    plt.axis("off")


def plot_cal_bars(data):
    weekShow = ((data['Duration']/np.timedelta64(1,'h')).groupby(data.Calendar)
            .resample('W').sum().unstack(level = 0)).round(1)

    #xlabels
    weekNames =  weekShow.set_index(weekShow.index.strftime("%b %d")).index.tolist()
    #mini bar names
    calNames = weekShow.columns.tolist()
    from nvd3 import multiBarChart
    from markupsafe import Markup
    chart = multiBarChart(width=1600, height=400, x_axis_format=None)
    xdata = weekNames
    extra_serie = {"tooltip": {"y_start": "You spent ", "y_end": " hours"}}
    for cal_name in weekShow:
        chart.add_serie(name=cal_name, y=weekShow[cal_name].tolist(), x=xdata,extra=extra_serie)
    chart.buildhtml()
    plot = Markup(chart.htmlcontent)
    return plot


    # months = [g for n, g in weekShow.groupby(pd.TimeGrouper('3M'))]
    # # pdb.set_trace()
    # from matplotlib.backends.backend_pdf import PdfPages
    # #pp = PdfPages('calData.pdf')
    # F = []
    # pdb.set_trace()
    # for dmonth in months:
    #     f = Figure()
    #     dmonth.set_index(dmonth.index.strftime("%b %d")).plot(kind = "bar")

    #     monthStart = dmonth.index[0].strftime("%B %Y")
    #     monthEnd = dmonth.index[len(dmonth)-1].strftime("%B %Y")
    #     plt.title('{} - {}'.format(monthStart,monthEnd))
    #     plt.ylabel('Time (hours)')
    #     plt.gcf().subplots_adjust(bottom = 0.15)
    #     plt.close()
    #     F.append(f)
    # return f
    #    pp.savefig()    
 #   pp.close()
    

    # for event in events:
    #     start = event['start'].get('dateTime', event['start'].get('date'))
    #     dt = datetime.fromtimestamp(rfc.tf_from_timestamp(start),Local)
    #     if event['summary'].lower() == 'Arrived At work'.lower():
    #         timeList.append([dt, []])
    #         i = i + 1
    #     if event['summary'].lower() == 'Left Work'.lower():
            
    #         if not timeList[len(timeList)-1][1]: #means there exists a arrival time for this session
    #             timeList[len(timeList)-1][1] = dt
    #         else:
    #             timeList.append([[],dt])        
    #     cond.append(event['summary'])
    #     print(start, event['summary'])




    # workTime = []
    # totTime = timedelta(0)
    # i = 1
    # for session in timeList:
    #     if session[0] and session[1]:
    #         dur = session[1] - session[0]
    #     else:
    #         print(session[0])
    #         print(session[1])
    #         # print('start time = {0}, end time = {1}'.format(session[0].strftime("%A, %d. %B %Y %I:%M%p"),session[1].strftime("%A, %d. %B %Y %I:%M%p"))
    #         dur = timedelta(0)
    #     workTime.append(dur)
    #     print('Session {0}: time = {1} hrs'.format(i, dur.total_seconds()/3600))
    #     totTime = workTime[len(workTime) - 1] + totTime
    #     i = i + 1
    # print('Total work this week: {0} hrs'.format(totTime))

# if event['summary'] == 'Arrived At Work':
#             arrivalTimes.append(start)
#         if event['summary'] == 'Left Work':
#             departTimes.append(start)

# if __name__ == '__main__':
#     main()