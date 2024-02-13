from functools import wraps
from http.client import (BAD_REQUEST, FORBIDDEN, NO_CONTENT,
                         REQUEST_ENTITY_TOO_LARGE, SEE_OTHER)
from urllib.parse import urljoin
from uuid import uuid4

import requests
from flask import (Blueprint, abort, g, make_response, redirect,
                   render_template, request)

from commons.models import Problem
from web.config import S3Config, SchedulerConfig
from web.const import Privilege, ReturnCode, String
from web.judge_manager import JudgeManager, NotFoundException
from web.problem_manager import ProblemManager
from web.user_manager import UserManager
from web.utils import generate_s3_public_url

admin = Blueprint('admin', __name__, static_folder='static')

def require_admin(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        if not g.is_admin:
            abort(FORBIDDEN)
        return func(*args, **kwargs)
    return wrapped

@admin.route('/')
@require_admin
def index():
    return render_template('admin.html')


# user

@admin.route('/user', methods=['post'])
def user_manager():
    if g.user is None or g.user.privilege < Privilege.SUPER:
        abort(FORBIDDEN)
    form = request.json
    if form is None:
        abort(BAD_REQUEST)
    # err = _validate_user_data(form)
    # if err is not None:
    #     return err
    try:
        op = int(form[String.TYPE])
        if op == 0:
            UserManager.add_user(form[String.USERNAME], form[String.STUDENT_ID], form[String.FRIENDLY_NAME],
                                  form[String.PASSWORD], form[String.PRIVILEGE])
            return ReturnCode.SUC_ADD_USER
        elif op == 1:
            UserManager.modify_user(form[String.USERNAME], form.get(String.STUDENT_ID, None),
                                     form.get(String.FRIENDLY_NAME, None), form.get(String.PASSWORD, None),
                                     form.get(String.PRIVILEGE, None))
            return ReturnCode.SUC_MOD_USER
        else:
            return ReturnCode.ERR_BAD_DATA
    except KeyError:
        return ReturnCode.ERR_BAD_DATA
    except TypeError:
        return ReturnCode.ERR_BAD_DATA


# problem

def reads_problem(func):
    @wraps(func)
    def wrapped(problem, *args, **kwargs):
        if not ProblemManager.can_read(problem):
            abort(FORBIDDEN)
        return func(problem, *args, **kwargs)
    return wrapped

def writes_problem(func):
    @wraps(func)
    def wrapped(problem, *args, **kwargs):
        if not ProblemManager.can_write(problem):
            abort(FORBIDDEN)
        return func(problem, *args, **kwargs)
    return wrapped

@admin.route('/problem/<problem:problem>/description', methods=['put'])
@writes_problem
def problem_description(problem: Problem):
    form = request.json
    if form is None:
        abort(BAD_REQUEST)
    for row in 'description', 'input', 'output', 'example_input', 'example_output', 'data_range':
        data = form.get(row, None)
        if data == 'None' or data == '':
            data = None
        setattr(problem, row, data)
    return make_response('', NO_CONTENT)

@admin.route('/problem/<problem:problem>/limit', methods=['put'])
@writes_problem
def problem_limit(problem: Problem):
    problem.limits = request.json
    return make_response('', NO_CONTENT)

@admin.route('/problem/<problem:problem>/upload-url')
@writes_problem
def data_upload(problem: Problem):
    return generate_s3_public_url('put_object', {
        'Bucket': S3Config.Buckets.problems,
        'Key': f'{problem.id}.zip',
    }, ExpiresIn=3600)


@admin.route('/problem/<problem:problem>/update-plan', methods=['POST'])
@writes_problem
def data_update(problem: Problem):
    url = urljoin(SchedulerConfig.base_url, f'problem/{problem.id}/update')
    res = requests.post(url).json()
    if res['result'] == 'ok':
        problem.languages_accepted = res['languages']
        return 'ok'
    elif res['result'] == 'invalid problem':
        return f'Invalid problem: {res["error"]}'
    elif res['result'] == 'system error':
        return f'System error: {res["error"]}'
    return 'Bad result from scheduler'

@admin.route('/problem/<problem:problem>/data-zip')
@reads_problem
def data_download(problem: Problem):
    key = f'{problem.id}.zip'
    url = generate_s3_public_url('get_object', {
        'Bucket': S3Config.Buckets.problems,
        'Key': key,
    }, ExpiresIn=3600)
    return redirect(url, SEE_OTHER)

def problem_admin_api(callback, success_retcode):
    type = request.form['type']

    if type == 'by_judge_id':
        id = request.form['judge_id']
        id_list = id.strip().splitlines()
        try:
            for i in id_list:
                submission = JudgeManager.get_submission(int(i))
                if submission is None:
                    raise NotFoundException
                if not ProblemManager.can_write(submission.problem):
                    raise NotFoundException
                callback(submission)
            return success_retcode
        except NotFoundException:
            return ReturnCode.ERR_BAD_DATA
    elif type == 'by_problem_id':
        ids = request.form['problem_id'].strip().splitlines()
        try:
            for id in ids:
                problem = ProblemManager.get_problem(int(id))
                if problem is None:
                    raise NotFoundException
                if not ProblemManager.can_write(problem):
                    raise NotFoundException
                JudgeManager.problem_judge_foreach(callback, id)
            return success_retcode
        except NotFoundException:
            return ReturnCode.ERR_BAD_DATA

@admin.route('/rejudge', methods=['POST'])
def rejudge():
    return problem_admin_api(JudgeManager.rejudge, ReturnCode.SUC_REJUDGE)

@admin.route('/mark-void', methods=['POST'])
def mark_void():
    return problem_admin_api(JudgeManager.mark_void, ReturnCode.SUC_DISABLE_JUDGE)

@admin.route('/abort-judge', methods=['POST'])
def abort_judge():
    return problem_admin_api(JudgeManager.abort_judge, ReturnCode.SUC_ABORT_JUDGE)


# misc

max_pic_size = 10485760

@admin.route('/pic-url', methods=['POST'])
@require_admin
def pic_upload():
    length = int(request.form['length'])
    if length > max_pic_size:
        abort(REQUEST_ENTITY_TOO_LARGE)
    if length <= 0:
        abort(BAD_REQUEST)
    type = str(request.form['type'])
    if not type.startswith('image/'):
        abort(BAD_REQUEST)
    return generate_s3_public_url('put_object', {
        'Bucket': S3Config.Buckets.images,
        'Key': str(uuid4()),
        'ContentLength': length,
        'ContentType': type,
    }, ExpiresIn=3600)
