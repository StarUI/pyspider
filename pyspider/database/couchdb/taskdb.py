import json, time, requests
from pyspider.database.base.taskdb import TaskDB as BaseTaskDB
from .couchdbbase import SplitTableMixin


class TaskDB(SplitTableMixin, BaseTaskDB):
    collection_prefix = ''

    def __init__(self, url, database='taskdb'):
        self.base_url = url
        # TODO: Add collection_prefix
        self.url = url + database + "/"
        self.database = database
        self.create_database(database)

        self.projects = set()
        self._list_project()

    def _get_collection_name(self, project):
        return self.database + "_" + self._collection_name(project)

    def _create_project(self, project):
        collection_name = self._get_collection_name(project)
        self.create_database(collection_name)
        #self.database[collection_name].ensure_index('status')
        #self.database[collection_name].ensure_index('taskid')
        self._list_project()
        print("[couchdb taskdb _create_project] Creating project: {}".format(project))

    def load_tasks(self, status, project=None, fields=None):
        if not project:
            self._list_project()

        if fields is None:
            fields = []

        if project:
            projects = [project, ]
        else:
            projects = self.projects

        for project in projects:
            collection_name = self._get_collection_name(project)
            for task in self.get_docs(collection_name, {"selector": {"status": status}, "fields": fields}):
            #for task in self.database[collection_name].find({'status': status}, fields):
                print("[couchdb taskdb load_tasks] status: {} project: {} fields: {} res: {}".format(status, project, fields, task))
                yield task

    def get_task(self, project, taskid, fields=None):
        if project not in self.projects:
            self._list_project()
        if project not in self.projects:
            print("[couchdb taskdb get_task] - project: {} not in projects".format(project))
            return
        if fields is None:
            fields = []
        collection_name = self._get_collection_name(project)
        ret = self.get_docs(collection_name, {"selector": {"taskid": taskid}, "fields": fields})
        #ret = self.database[collection_name].find_one({'taskid': taskid}, fields)
        if len(ret) == 0:
            return None
        return ret[0]

    def status_count(self, project):
        if project not in self.projects:
            self._list_project()
        if project not in self.projects:
            return {}
        collection_name = self._get_collection_name(project)

        def _count_for_status(collection_name, status):
            total = len(self.get_docs(collection_name, {"selector": {'status': status}}))
            #total = collection.find({'status': status}).count()
            return {'total': total, "_id": status} if total else None

        c = collection_name
        ret = filter(lambda x: x,map(lambda s: _count_for_status(c, s), [self.ACTIVE, self.SUCCESS, self.FAILED]))
        print('[couchdb taskdb status_count] ret: {}'.format(ret))

        result = {}
        if isinstance(ret, dict):
            ret = ret.get('result', [])
        for each in ret:
            result[each['_id']] = each['total']
        return result

    def insert(self, project, taskid, obj={}):
        if project not in self.projects:
            self._create_project(project)
        obj = dict(obj)
        obj['taskid'] = taskid
        obj['project'] = project
        obj['updatetime'] = time.time()
        print("[couchdb taskdb insert] taskid: {} project: {} obj: {}".format(taskid, project, obj))
        return self.update(project, taskid, obj=obj)

    def update(self, project, taskid, obj={}, **kwargs):
        obj = dict(obj)
        obj.update(kwargs)
        obj['updatetime'] = time.time()
        collection_name = self._get_collection_name(project)
        return self.update_doc(collection_name, taskid, obj)

    def drop_database(self):
        res = self.delete(self.url)
        return res

    def drop(self, project):
        collection_name = self._get_collection_name(project)
        url = self.base_url + collection_name
        res = self.delete(url)
        return res