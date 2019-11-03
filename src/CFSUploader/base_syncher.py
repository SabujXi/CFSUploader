import wx
from pubsub import pub
from cpath import CRoot
from threading import Thread


class CPathSyncTask:
    def __init__(self, cpath, action):
        assert action in ('UPLOAD', 'DELETE')
        self._cpath = cpath
        self._action = action

    @property
    def cpath(self):
        return self._cpath

    @property
    def action(self):
        return self._action

    def is_delete(self):
        return self._action == 'DELETE'

    def is_upload(self):
        return self._action == 'UPLOAD'


class BaseSyncher:
    def __init__(self, project_base_path, last_snapshot_cpaths, login, ignorer):
        super().__init__()
        self._project_base_path = project_base_path
        self._last_snapshot_cpaths = last_snapshot_cpaths
        self._login = login
        self._ignorer = ignorer
        self._pause = False

        self._cpath_sync_tasks = []

        self._prepared = False

        self._subscriber = pub.subscribe(self.on_pause_request, 'pause_syncher')

    def sync(self):
        pass

    def connect(self):
        pass

    def disconnect(self):
        pass

    def notify_cpath_deleted(self, cpath):
        wx.CallAfter(pub.sendMessage, 'cpath_deleted', cpath=cpath)

    def notify_cpath_uploaded(self, cpath):
        wx.CallAfter(pub.sendMessage, 'cpath_uploaded', cpath=cpath)

    def notify_sync_completed(self, msg):
        wx.CallAfter(pub.sendMessage, 'sync_completed', msg=msg)

    def notify_sync_paused(self, msg):
        wx.CallAfter(pub.sendMessage, 'sync_paused', msg=msg)

    def notify_sync_error(self, msg):
        wx.CallAfter(pub.sendMessage, 'sync_error', msg=msg)

    def on_pause_request(self):
        self._pause = True

    def _prepare(self):
        if self._prepared:
            return
        root2 = CRoot(self._project_base_path, self._ignorer)
        root2.load()

        root1 = CRoot(self._project_base_path, self._ignorer)
        root1.load_from_path_dicts([cpath.as_path_dict() for cpath in self._last_snapshot_cpaths])

        diff = root1.diff(root2)
        if not diff.changed():
            print("Project up to date, nothing to sync.")
        # deleted
        for cpath in diff.deleted:
            # Delete this path
            self._cpath_sync_tasks.append(CPathSyncTask(cpath, 'DELETE'))
        # -> upload: new, modified
        upload_cpaths = [*diff.new, *diff.modified]
        for cpath in upload_cpaths:
            self._cpath_sync_tasks.append(CPathSyncTask(cpath, 'UPLOAD'))
        self._prepared = True

    def run(self):
        class SyncThread(Thread):
            def __init__(self, syncher):
                super().__init__()
                self._syncher = syncher

            def run(self) -> None:
                try:
                    self._syncher.sync()
                except Exception as ex:
                    self._syncher.notify_sync_error(str(ex))
        SyncThread(self).start()
