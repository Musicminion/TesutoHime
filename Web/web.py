from flask import Flask, request, render_template, redirect, make_response, abort
from uuid import uuid4
import re
from sessionManager import Login_Manager
from userManager import User_Manager
from problemManager import Problem_Manager
from discussManager import Discuss_Manager
from judgeManager import Judge_Manager
from contestManager import Contest_Manager
from judgeServerScheduler import JudgeServer_Scheduler
from config import LoginConfig, WebConfig, JudgeConfig, ProblemConfig
from utils import *
from admin import admin

web = Flask('WEB')
web.register_blueprint(admin)

@web.errorhandler(500)
def Error_500():
    return "Internal Server Error: invalid Request"

@web.route('/')
def Index():
    return render_template('index.html')

@web.route('/get_username', methods=['POST'])
def Get_Username():
    return Login_Manager.Get_FriendlyName()

@web.route('/login', methods=['GET', 'POST'])
def Login():
    if request.method == 'GET':
        next = request.args.get('next')
        next = '/' if next == None else next
        if Login_Manager.Check_User_Status():
            return render_template('login.html', Logged_In = True, Next = next) # display 'Plsease Logout First'
        return render_template('login.html', Logged_In = False, Next = next)
    Username = request.form.get('username')
    Password = request.form.get('password')
    if not User_Manager.Check_Login(Username, Password): # no need to avoid sql injection
        return '-1'
    lid = str(uuid4())
    Login_Manager.New_Session(Username, lid)
    ret = make_response('0')
    ret.set_cookie(key = 'Login_ID', value = lid, max_age = LoginConfig.Login_Life_Time)
    return ret

def Validate(Username: str, Password: str, Friendly_Name: str, Student_ID: str) -> int:
    Username_Reg = '([a-zA-Z][a-zA-Z0-9_]{0,19})$'
    Password_Reg = '([a-zA-Z0-9_\!\@\#\$\%\^&\*\(\)]{6,30})$'
    Friendly_Name_Reg = '([a-zA-Z0-9_]{1,60})$'
    Student_ID_Reg = '([0-9]{12})$'
    if Username == 'Nobody' or Friendly_Name == 'Nobody':
        return -1
    if re.match(Username_Reg, Username) == None:
        return -1
    if re.match(Password_Reg, Password) == None:
        return -1
    if re.match(Friendly_Name_Reg, Friendly_Name) == None:
        return -1
    if re.match(Student_ID_Reg, Student_ID) == None:
        return -1
    return 0 if User_Manager.Validate_Username(Username) else -1

@web.route('/register', methods=['GET', 'POST'])
def Register():
    if request.method == 'GET':
        if Login_Manager.Check_User_Status():
            return render_template('register.html', Logged_In = True, Next = next) # display 'Plsease Logout First'
        return render_template('register.html', Logged_In = False, Next = next)
    Username = request.form.get('username')
    Password = request.form.get('password')
    Friendly_Name = request.form.get('friendly_name')
    Student_ID = request.form.get('student_id')
    val = Validate(Username, Password, Friendly_Name, Student_ID)
    if val == 0:
        User_Manager.Add_User(Username, Student_ID, Friendly_Name, Password, '0')
    return str(val)

@web.route('/problems')
def Problem_List():
    if not Login_Manager.Check_User_Status():
        return redirect('login?next=' + request.url)
    Page = request.args.get('page')
    Page = int(Page) if Page != None else 1
    max_Page = int((Problem_Manager.Get_Max_ID() - 999 + WebConfig.Problems_Each_Page - 1) / WebConfig.Problems_Each_Page)
    Page = max(min(max_Page, Page), 1)
    startID = (Page - 1) * WebConfig.Problems_Each_Page + 1 + 999
    endID = Page * WebConfig.Problems_Each_Page + 999
    Problems = Problem_Manager.Problem_In_Range(startID, endID, UnixNano())
    return render_template('problem_list.html', Problems = Problems, Pages = Gen_Page(Page, max_Page))

@web.route('/problem')
def Problem_Detail():
    if not Login_Manager.Check_User_Status():
        return redirect('login?next=' + request.url)
    id = request.args.get('problem_id')
    if id == None:
        return redirect('/') # No argument fed
    Detail = Problem_Manager.Get_Problem(id)
    In_Contest = Problem_Manager.In_Contest(id) and Login_Manager.Get_Privilege() <= 0
    return render_template('problem_details.html', Detial = Detail, In_Contest = In_Contest)

@web.route('/submit', methods=['GET', 'POST'])
def Submit_Problem():
    if request.method == 'GET':
        if not Login_Manager.Check_User_Status():
            return redirect('login?next=' + request.url)
        if request.args.get('problem_id') == None:
            return redirect('/')
        Problem_ID = int(request.args.get('problem_id'))
        Title = Problem_Manager.Get_Title(Problem_ID)
        Username = Login_Manager.Get_Username()
        return render_template('problem_submit.html', Problem_ID = Problem_ID, Title = Title)
    else:
        if not Login_Manager.Check_User_Status():
            return redirect('login')
        Problem_ID = int(request.form.get('problem_id'))
        if Problem_ID < 1000 or Problem_ID > Problem_Manager.Get_Max_ID():
            abort(404)
        if UnixNano() < Problem_Manager.Get_Release_Time(int(Problem_ID)) and Login_Manager.Get_Privilege() <= 0:
            return '-1'
        Username = Login_Manager.Get_Username()
        Lang = request.form.get('lang') # cpp or git
        Code = request.form.get('code')
        if len(str(Code)) > ProblemConfig.Max_Code_Length:
            return '-1'
        JudgeServer_Scheduler.Start_Judge(Problem_ID, Username, Code, Lang)
        return '0'

@web.route('/rank')
def Problem_Rank():
    if not Login_Manager.Check_User_Status():
        return redirect('login?next=' + request.url)
    Problem_ID = request.args.get('problem_id')
    if Problem_ID == None:
        return redirect('/')
    Sort_Parameter = request.args.get('sort_param')
    if Sort_Parameter != 'time' and Sort_Parameter != 'memory' and Sort_Parameter != 'submit_time':
        Sort_Parameter = 'time'
    Record = Judge_Manager.Search_AC(Problem_ID)
    for i in range(0, len(Record)): # ID, User, Time_Used, Mem_Used, Language, Time
        Record[i][2] = int(Record[i][2])
        Record[i][3] = int(Record[i][3])
        Record[i][5] = int(Record[i][5])
    if Sort_Parameter == 'time':
        Record = sorted(Record, key = lambda x, y: x[2] < y[2])
    elif Sort_Parameter == 'memory':
        Record = sorted(Record, key = lambda x, y: x[3] < y[3])
    elif Sort_Parameter == 'memory':
        Record = sorted(Record, key = lambda x, y: x[5] < y[5])
    return render_template('problem_rank.html', Problem_ID = Problem_ID, Title = Problem_Manager.Get_Title(Problem_ID), Data = Record)


@web.route('/discuss', methods=['GET', 'POST'])
def Discuss(): # todo: Debug discuss
    if request.method == 'GET':
        if not Login_Manager.Check_User_Status():
            return redirect('login?next=' + request.url)
        Problem_ID = int(request.args.get('problem_id'))
        if Problem_ID == None:
            return redirect('/')
        if Problem_Manager.In_Contest(Problem_ID) and Login_Manager.Get_Privilege() <= 0: # Problem in Contest or Homework and Current User is NOT administrator
            return render_template('problem_discussion.html', Problem_ID = Problem_ID, Title = Problem_Manager.Get_Title(Problem_ID), Blocked = True) # Discussion Closed
        Username = Login_Manager.Get_Username() # for whether to display edit or delete
        Privilge = Login_Manager.Get_Privilege()
        Data = Discuss_Manager.Get_Discuss_For_Problem(Problem_ID)
        Discuss = []
        for ele in Data:
            tmp = [ele[0], ele[1], Readable_Time(int(ele[2]))]
            if ele[0] == Username or Privilge == 2: # ele[3]: editable?
                tmp.append(True)
            else:
                tmp.append(False)
            Discuss.append(tmp)
        return render_template('problem_discussion.html', Title = Problem_Manager.Get_Title(Problem_ID), Discuss = Discuss)
    else:
        if not Login_Manager.Check_User_Status():
            return redirect('login')
        Action = request.form.get('action') # post, edit, delete
        Problem_ID = int(request.form.get('problem_id')) # this argument must be given
        if Action == 'post':
            Text = request.form.get('text')
            Username = Login_Manager.Get_Username()
            Discuss_Manager.Add_Discuss(Problem_ID, Username, Text)
            return redirect('/discuss?problem_id=' + Problem_ID)
        if Action == 'edit':
            Discuss_ID = int(request.form.get('id'))
            Text = request.form.get('text')
            Username = Login_Manager.Get_Username()
            if Username == Discuss_Manager.Get_Author(Discuss_ID) or Login_Manager.Get_Privilege() > 0: # same user or administrator
                Discuss_Manager.Modify_Discuss(Discuss_ID, Text)
            else:
                print('Access Dined in Discuss: Edit')
            return redirect('/discuss?problem_id=' + Problem_ID)
        if Action == 'delete':
            Discuss_ID = int(request.form.get('id'))
            Username = Login_Manager.Get_Username()
            if Username == Discuss_Manager.Get_Author(Discuss_ID) or Login_Manager.Get_Privilege() > 0: # same user or administrator
                Discuss_Manager.Delete_Discuss(Discuss_ID)
            else:
                print('Access Dined in Discuss: Delete')
            return redirect('/discuss?problem_id=' + Problem_ID)
        else: # what happened?
            return redirect('/discuss?problem_id=' + Problem_ID)

@web.route('/status')
def Status():
    if not Login_Manager.Check_User_Status():
        return redirect('login?next=' + request.url)

    Page = request.args.get('page')
    Arg_Submitter = request.args.get('submitter')
    Arg_Problem_ID = request.args.get('problem_id')
    Username = Login_Manager.Get_Username()
    Privilege = Login_Manager.Get_Privilege()

    if Arg_Submitter == None and Arg_Problem_ID == None:
        Page = int(Page) if Page != None else 1
        max_Page = int((Judge_Manager.Max_ID() + JudgeConfig.Judge_Each_Page - 1) / JudgeConfig.Judge_Each_Page)
        Page = max(min(max_Page, Page), 1)
        endID = Judge_Manager.Max_ID() - (Page - 1) * JudgeConfig.Judge_Each_Page
        startID = endID - JudgeConfig.Judge_Each_Page + 1
        Record = Judge_Manager.Judge_In_Range(startID, endID)
        Data = []
        for ele in Record:
            cur = {}
            cur['ID'] = ele['ID']
            cur['Friendly_Name'] = User_Manager.Get_Friendly_Name(ele['Username'])
            cur['Problem_ID'] = ele['Problem_ID']
            cur['Problem_Title'] = Problem_Manager.Get_Title(ele['Problem_ID'])
            cur['Status'] = ele['Status']
            cur['Time_Used'] = ele['Time_Used']
            cur['Mem_Used'] = ele['Mem_Used']
            cur['Lang'] = ele['Lang']
            cur['Visible'] = Username == ele['Username'] or Privilege == 2 # Same User or login as Super Admin
            cur['Time'] = Readable_Time(ele['Time'])
            Data.append(cur)
        return render_template('status.html', Data = Data, Pages = Gen_Page(Page, max_Page))
    else:
        Record = Judge_Manager.Search_Judge(Arg_Submitter, Arg_Problem_ID)
        max_Page = int((len(Record) + JudgeConfig.Judge_Each_Page - 1) / JudgeConfig.Judge_Each_Page)
        Page = max(min(max_Page, Page), 1)
        endID = len(Record) - (Page - 1) * JudgeConfig.Judge_Each_Page
        startID = max(endID - JudgeConfig.Judge_Each_Page + 1, 1)
        Record = Record[startID - 1: endID - 1]
        Data = []
        for ele in Record:
            cur = {}
            cur['ID'] = ele['ID']
            cur['Friendly_Name'] = User_Manager.Get_Friendly_Name(ele['Username'])
            cur['Problem_ID'] = ele['Problem_ID']
            cur['Problem_Title'] = Problem_Manager.Get_Title(ele['Problem_ID'])
            cur['Status'] = ele['Status']
            cur['Time_Used'] = ele['Time_Used']
            cur['Mem_Used'] = ele['Mem_Used']
            cur['Lang'] = ele['Lang']
            cur['Visible'] = Username == ele['Username'] or Privilege == 2 # Same User or login as Super Admin
            cur['Time'] = Readable_Time(ele['Time'])
            Data.append(cur)
        return render_template('status.html', Data = Data, Pages = Gen_Page(Page, max_Page), Submitter = Arg_Submitter, Problem_ID = Arg_Problem_ID)



@web.route('/code')
def Code(): # todo: View Judge Detail
    if not Login_Manager.Check_User_Status(): # not login
        return redirect('login?next=' + request.url)
    if request.args.get('run_id') == None: # bad argument
        return redirect('/')
    run_id = int(request.args.get('run_id'))
    judge = Judge_Manager.Search_Judge(run_id)
    if judge == {}: # bad argument
        return redirect('/')
    if Login_Manager.Get_Username() != judge['User']:
        return render_template('code.html', Blocked = True)
    else:
        return 'Hua Q'


@web.route('/contest')
def Contest(): # todo: debug Contest and homework
    if not Login_Manager.Check_User_Status():
        return redirect('login?next=' + request.url)
    Contest_ID = request.args.get('contest_id')
    if Contest_ID == None: # display contest list
        List = Contest_Manager.List_Contest(0)
        Data = []
        curTime = UnixNano()
        for ele in List:
            cur = {}
            cur['ID'] = int(ele[0])
            cur['Title'] = str(ele[1])
            cur['Start_Time'] = Readable_Time(int(ele[2]))
            cur['End_Time'] = Readable_Time(int(ele[3]))
            if curTime < int(ele[2]):
                cur['Status'] = 'Pending'
            elif curTime > int(ele[3]):
                cur['Status'] = 'Finished'
            else:
                cur['Status'] = 'Going On'
            Data.append(cur)
        return render_template('contest_list.html', Data = Data)
    else:
        Contest_ID = int(Contest_ID)
        StartTime, Endtime = Contest_Manager.Get_Time(Contest_ID)
        Problems = Contest_Manager.List_Player_For_Contest(Contest_ID)
        Players = Contest_Manager.List_Player_For_Contest(Contest_ID)
        Data = []
        for Player in Players:
            tmp = [0, 0, ]
            for Problem in Problems:
                Submits = Judge_Manager.Get_Contest_Judge(int(Problem), Player, StartTime, Endtime)
                maxScore = 0
                isAC = False
                Submit_Time = 0
                for Submit in Submits:
                    maxScore = max(maxScore, int(Submit[2]))
                    Submit_Time += 1
                    if Submit[1] == 'AC':
                        isAC = True
                        tmp[1] += int(Submit[3]) - StartTime + (Submit_Time - 1) * 1200
                tmp[0] += maxScore
                tmp.append([isAC, Submit_Time]) # AC try time or failed times
            Data.append(tmp)
        Data = sorted(Data, key = lambda x, y: x[1] < y[1] if x[0] == y[0] else x[0] > y[0])
        return render_template('contest.html', StartTime = StartTime, Endtime = Endtime, Problems = Problems, Players = Players, Data = Data)

@web.route('/homework')
def Homework():
    if not Login_Manager.Check_User_Status():
        return redirect('login?next=' + request.url)
    Contest_ID = request.args.get('contest_id')
    if Contest_ID == None: # display contest list
        List = Contest_Manager.List_Contest(1)
        Data = []
        curTime = UnixNano()
        for ele in List:
            cur = {}
            cur['ID'] = int(ele[0])
            cur['Title'] = str(ele[1])
            cur['Start_Time'] = Readable_Time(int(ele['Start_Time']))
            cur['End_Time'] = Readable_Time(int(ele['End_Time']))
            if curTime < int(ele['Start_Time']):
                cur['Status'] = 'Pending'
            elif curTime > int(ele['End_Time']):
                cur['Status'] = 'Finished'
            else:
                cur['Status'] = 'Going On'
            Data.append(cur)
        return render_template('homework_list.html', Data = Data)
    else:
        Contest_ID = int(Contest_ID)
        StartTime, Endtime = Contest_Manager.Get_Time(Contest_ID)
        Problems = Contest_Manager.List_Problem_For_Contest(Contest_ID)
        Players = Contest_Manager.List_Player_For_Contest(Contest_ID)
        Data = []
        for Player in Players:
            tmp = [0, ]
            for Problem in Problems:
                Submits = Judge_Manager.Get_Contest_Judge(int(Problem), Player, StartTime, Endtime)
                isAC = False
                for Submit in Submits:
                    if Submit[1] == 'AC':
                        isAC = True
                if isAC:
                    tmp[0] += 1
                tmp.append([isAC]) # AC try time or failed times
            Data.append(tmp)
        return render_template('homework.html', StartTime = StartTime, Endtime = Endtime, Problems = Problems, Players = Players, Data = Data)

@web.route('/about')
def About():
    return 'Hua Q~'