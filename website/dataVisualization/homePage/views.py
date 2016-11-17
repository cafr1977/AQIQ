import os
import pandas as pd
import json
import datetime as datetime
from django.shortcuts import render,redirect
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.http import HttpResponse,JsonResponse
from models import Document
from forms import DocumentForm, LoginForm, CreateUserForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.files import File
from wsgiref.util import FileWrapper
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

import csv





def create_user_view(request):
    if request.method == 'GET':
        form = CreateUserForm()
        return render(request, 'create_user.html', {'form': form})
    elif request.method == 'POST':
        form = CreateUserForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data['email_address']
            password = form.cleaned_data['password']
            confirm_password = form.cleaned_data['password_repeat']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']

            if password == confirm_password:
                # check if user exists
                user = User.objects.filter(username=email).first()
                if not user:
                    new_user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name
                    )
                    new_user.save()
                    return HttpResponseRedirect('/')
                else:
                    error = {
                        'msg': 'Account already exists'
                    }
                    return render(request, 'create_user.html', {
                        'form': form,
                        'error': error
                    })
            else:
                error = {
                    'msg': 'Passwords are not the same'
                }
                return render(request, 'create_user.html', {
                    'form': form,
                    'error': error
                })



def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            # authenticate
            email = form.cleaned_data['email_address']
            password = form.cleaned_data['password']

            user = authenticate(
                username=email,
                password=password
            )

            if user is not None:
                # authenticated
                # log in the user
                login(request, user)

                next_url = request.POST.get('next', None)

                if next_url:
                    print 'Got Next parameter'
                    return HttpResponseRedirect(next_url)

                return render(request, 'index.html', {
                    'user': user
                })
            else:
                # not authenticated
                error = {
                    'msg': 'Could not validate credentials'
                }
                return render(request, 'login.html', {
                    'form': form,
                    'error': error
                })

    else:
        user = request.user
        if user and user.is_authenticated():
            return HttpResponseRedirect('/')
        form = LoginForm()
        return render(request, 'login.html', {
            'form': form
        })


@login_required
def home_view(request):
    return render(request, 'index.html', {
        'user': request.user
    })


@login_required
def logout_view(request):
    user = request.user
    if user and user.is_authenticated():
        # log the user out
        logout(request)
    # redirect to login
    return HttpResponseRedirect('/')


def index(request):
    return render(
        request,
        'index.html'
        )


@login_required
def documents(request):
    locationOfDocument=os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/media' + request.path
    print locationOfDocument
    outputContent = []
    with open(locationOfDocument) as fileHandler:
        for line in fileHandler:
            dictContent = {}
            line = line.strip()
            if(len(line) > 0):
                splitLine = line.split(',')
                dictContent['date'] = splitLine[1] + " " + splitLine[2]
                # datetime.datetime.strptime(splitLine[1] + " " + splitLine[2],'%Y-%m-%d %H:%M:%S')
                dictContent['temperature'] = splitLine[6]
                outputContent.append(dictContent)
    # print json.dumps(outputContent)

    return render(
        request,
        'display.html',
        {'displayContent': json.dumps(outputContent)}
        )


@login_required
def display(request, locationOfDocument):
    print locationOfDocument
    outputContent = []
    with open(locationOfDocument) as fileHandler:
        for line in fileHandler:
            dictContent = {}
            line = line.strip()
            if(len(line) > 0):
                splitLine = line.split(',')
                dictContent['Date'] = splitLine[1] + " " + splitLine[2]
                dictContent['Temperature'] = splitLine[15]
                outputContent.append(dictContent)
    # print json.dumps(outputContent)

    return render(
        request,
        'display.html',
        {'displayContent': json.dumps(outputContent)}
        )


@login_required
def uploadedFiles(request):
    # Load documents for the list page
    documents = Document.objects.all()

    return render(
        request,
        'displayUploadedFiles.html',
        {'documents': documents}
        )



@login_required
def personalUploadedFiles(request):
    # Load documents for the list page
    documents = Document.objects.filter(userName=request.user.first_name)

    return render(
        request,
        'personalDisplayUploadedFiles.html',
        {'documents': documents}
        )


def averaging(path,fileName):
    
    df = pd.read_csv("media/"+path,header=0,usecols=[1,2,5,6,7,19,21,25],names=["oldDate", "Time", "Temperature","Humidity","CO2","fig210_sens","fig280_sens","e2vo3_sens"],delimiter=",")
    df['Date'] = pd.to_datetime(df['oldDate'] + ' ' + df['Time'])
    times = pd.DatetimeIndex(df.Date)

    # # Minute Averaging
    groupedMinute = df.groupby([times.date, times.hour, times.minute])['Temperature','Humidity',"CO2","fig210_sens","fig280_sens","e2vo3_sens"].mean().reset_index()
    groupedMinute['Date'] =  pd.to_datetime(groupedMinute['level_0']) +  (pd.to_timedelta(groupedMinute['level_1'],unit='h') + pd.to_timedelta(groupedMinute['level_2'],unit='m'))
    groupedMinute.drop(['level_0','level_1','level_2'],axis=1,inplace=True)
    groupedMinute = groupedMinute[['Date','Temperature', 'Humidity', 'CO2', 'fig210_sens', 'fig280_sens', 'e2vo3_sens']]

    # # Hour Averaging
    groupedHour = df.groupby([times.date, times.hour])['Temperature','Humidity',"CO2","fig210_sens","fig280_sens","e2vo3_sens"].mean().reset_index()
    groupedHour['Date'] =  pd.to_datetime(groupedHour['level_0']) +  (pd.to_timedelta(groupedHour['level_1'],unit='h'))
    groupedHour.drop(['level_0','level_1'],axis=1,inplace=True)
    groupedHour = groupedHour[['Date','Temperature', 'Humidity', 'CO2', 'fig210_sens', 'fig280_sens', 'e2vo3_sens']]

    # # Day Averaging
    groupedDaily = df.groupby([times.date])['Temperature','Humidity',"CO2","fig210_sens","fig280_sens","e2vo3_sens"].mean().reset_index()
    groupedDaily['Date'] =  pd.to_datetime(groupedDaily['index'])
    groupedDaily.drop(['index'],axis=1,inplace=True)
    groupedDaily = groupedDaily[['Date','Temperature', 'Humidity', 'CO2', 'fig210_sens', 'fig280_sens', 'e2vo3_sens']]

    fileName = fileName.split(".")[0]

    groupedMinute.to_csv(fileName + "_" + path.split(".")[0] + '_minute' + ".csv",index=False)
    groupedHour.to_csv(fileName + "_" + path.split(".")[0] + '_hour' + ".csv",index=False)
    groupedDaily.to_csv(fileName + "_" + path.split(".")[0] + '_daily' + ".csv",index=False)

    os.remove("media/" + path)

    return fileName + "_" + path.split(".")[0]

# def hourAveraging(path,fileName):    
#     # # Hourly Averaging
#     df = pd.read_csv("media/"+path,header=0,usecols=[1,2,5,6,7,19,21,25],names=["oldDate", "Time", "Temperature","Humidity","CO2","fig210_sens","fig280_sens","e2vo3_sens"],delimiter=",")
#     df['Date'] = pd.to_datetime(df['oldDate'] + ' ' + df['Time'])
#     times = pd.DatetimeIndex(df.Date)

#     grouped = df.groupby([times.date, times.hour])['Temperature','Humidity',"CO2","fig210_sens","fig280_sens","e2vo3_sens"].mean().reset_index()
#     grouped['Date'] =  pd.to_datetime(grouped['level_0']) +  (pd.to_timedelta(grouped['level_1'],unit='h'))
#     grouped.drop(['level_0','level_1'],axis=1,inplace=True)
#     grouped = grouped[['Date','Temperature', 'Humidity', 'CO2', 'fig210_sens', 'fig280_sens', 'e2vo3_sens']]


# # Daily Averaging

# df = pd.read_csv('test.txt',header=0,usecols=[1,2,5,6,7,19,21,25],names=["oldDate", "Time", "Temperature","Humidity","CO2","fig210_sens","fig280_sens","e2vo3_sens"],delimiter=",")
# df['Date'] = pd.to_datetime(df['oldDate'] + ' ' + df['Time'])
# times = pd.DatetimeIndex(df.Date)
# grouped = df.groupby([times.date])['Temperature','Humidity',"CO2","fig210_sens","fig280_sens","e2vo3_sens"].mean().reset_index()
# grouped['Date'] =  pd.to_datetime(grouped['index'])
# grouped.drop(['index'],axis=1,inplace=True)
# grouped = grouped[['Date','Temperature', 'Humidity', 'CO2', 'fig210_sens', 'fig280_sens', 'e2vo3_sens']]



@login_required
def uploadAFile(request):
    # Handle file upload
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        some_file = File(request.FILES['docfile'])
        

        
        # import pdb
        # pdb.set_trace()
        # print averageMinuteFileContent
        if form.is_valid():
            path = default_storage.save('averaging.txt', ContentFile(some_file.read()))

            averageFileName = averaging(path,some_file.name)

            averageMinuteFile = averageFileName + '_minute.csv'
            averageHourFile = averageFileName + '_hour.csv'
            averageDailyFile = averageFileName + '_daily.csv'

            fileHandlerMinute = open(averageMinuteFile, 'rb')
            fileHandlerHour = open(averageHourFile, 'rb')
            fileHandlerDay = open(averageDailyFile, 'rb')


            averageMinuteFileHandle = File(fileHandlerMinute)
            averageHourFileHandle = File(fileHandlerHour)
            averageDayFileHandle = File(fileHandlerDay)


            # print averageMinuteFileHandle.__dict__
            # print some_file.__dict__
            newdoc = Document(podId=request.POST['podId'],
                              location=request.POST['location'],
                              startDate=request.POST['startDate'],
                              endDate=request.POST['endDate'],
                              podUseType=request.POST['podUseType'],
                              pollutantOfInterest=request.POST['pollutantOfInterest'],
                              podUseReason=request.POST['podUseReason'],
                              projectName=request.POST['projectName'],
                              mentorName=request.POST['mentorName'],
                              school=request.POST['school'],
                              userName=request.user.first_name,
                              docfile=some_file,
                              averageMinuteFile=averageMinuteFileHandle,
                              averageHourFile=averageHourFileHandle,
                              averageDayFile=averageDayFileHandle
                              # averageMinuteFile=averageMinuteFileHandle
                             )

            # print request.FILES['docfile']
            newdoc.save()
            os.remove(averageMinuteFile)
            os.remove(averageHourFile)
            os.remove(averageDailyFile)

            # Redirect to the document list after POST
            return HttpResponseRedirect(reverse('uploadedFiles'))
    else:
        form = DocumentForm()  # A empty, unbound form
    # Render list page with the documents and the form
    return render(
        request,
        'upload.html',
        {'form': form}
        )


@login_required
def getRawCSV(request,locationOfDocument1):
    filename = "media/" + locationOfDocument1
    if filename:
        output_file = FileWrapper(open(filename, 'rb'))
        response = HttpResponse(output_file,content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=%s' % (locationOfDocument1)
        return response
    return  HttpResponseNotFound('<h1>File not found</h1>')



@login_required
def getSelectedCSV(request,locationOfDocument1):
    filename = "media/" + locationOfDocument1
    if filename:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=%s' % (locationOfDocument1.split(".")[0] + ".csv")
        writer = csv.writer(response)
        writer.writerow(['Date', 'Temperature', 'Humidity', 'CO2', 'fig210_sens', 'fig280_sens', 'e2vo3_sens'])
        with open(filename) as fileHandler:
            for line in fileHandler:
                line = line.strip()
                if(len(line) > 0):
                    splitLine = line.split(',')
                    writer.writerow([splitLine[1] + " " + splitLine[2],splitLine[5],splitLine[6],splitLine[7],splitLine[19],splitLine[21],splitLine[25]])
        return response
    return  HttpResponseNotFound('<h1>File not found</h1>')


def getContentsOfTxtFile(locationOfDocument):
    outputContent = []
    with open("media/"+locationOfDocument) as fileHandler:
        for line in fileHandler:
            dictContent = {}
            line = line.strip()
            if(len(line) > 0):
                splitLine = line.split(',')
                dictContent['Date'] = splitLine[1] + " " + splitLine[2]
                dictContent['Temperature'] = splitLine[5]
                dictContent['Humidity'] = splitLine[6]
                dictContent['CO2'] = splitLine[7]
                dictContent['fig210_sens'] = splitLine[19]
                dictContent['fig280_sens'] = splitLine[21]
                dictContent['e2vo3_sens'] = splitLine[25]
                outputContent.append(dictContent)
    return outputContent

def getContentsOfCSVFile(locationOfDocument):
    outputContent = []
    with open("media/"+locationOfDocument) as fileHandler:
        for line in fileHandler:
            dictContent = {}
            line = line.strip()
            if(len(line) > 0):
                splitLine = line.split(',')
                dictContent['Date'] = splitLine[0]
                dictContent['Temperature'] = splitLine[1]
                dictContent['Humidity'] = splitLine[2]
                dictContent['CO2'] = splitLine[3]
                dictContent['fig210_sens'] = splitLine[4]
                dictContent['fig280_sens'] = splitLine[5]
                dictContent['e2vo3_sens'] = splitLine[6]
                outputContent.append(dictContent)
    return outputContent



@login_required
def dataAnalysis(request, locationOfDocument1, locationOfDocument2):
    
    # Both file names are provided - Must Ideally never happen
    if locationOfDocument2 == "":
        if locationOfDocument1 == "":
            return render(request,'displayDataAnalysis.html')

    # Only one file name is provided - TXT or CSV
        outputContent1 = []
        if locationOfDocument1.split(".")[1] == "txt":
            outputContent1 = getContentsOfTxtFile(locationOfDocument1)
            return render(request,'displayDataAnalysis.html', {'displayContent1': json.dumps(outputContent1)})
        else:
            outputContent1 = getContentsOfCSVFile(locationOfDocument1)
            return render(request,'displayDataAnalysis.html',{'displayContent1': json.dumps(outputContent1)})

    # Two file names are provided - TXT or CSV
    else:
        outputContent1 = []
        outputContent2 = []

        # Processing for the 1st file
        if locationOfDocument1.split(".")[1] == "txt":
            outputContent1 = getContentsOfTxtFile(locationOfDocument1)
        else:
            outputContent1 = getContentsOfCSVFile(locationOfDocument1)

        # Processing for the 2nd file
        if locationOfDocument2.split(".")[1] == "txt":
            outputContent2 = getContentsOfTxtFile(locationOfDocument2)
        else:
            outputContent2 = getContentsOfCSVFile(locationOfDocument2)

        return render(request,'displayDataAnalysis.html',{'displayContent1': json.dumps(outputContent1),'displayContent2': json.dumps(outputContent2)})

@login_required
def multipleDataAnalysis(request, locationOfDocument1, locationOfDocument2):
    print locationOfDocument1 + " " + locationOfDocument2