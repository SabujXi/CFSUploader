from uploaders.base_syncher import BaseSyncher
import paramiko
import os


class SFTPSyncher(BaseSyncher):
    def __init__(self, project_base_path, last_snapshot_cpaths, login, ignorer):
        super().__init__(project_base_path, last_snapshot_cpaths, login, ignorer)
        self.sftp = None

    def connect(self):
        login = self._login
        host = login.host
        port = login.port
        username = login.username
        password = login.password
        # remote_dir = login.
        transport = paramiko.Transport((host, port))
        transport.connect(None, username, password)
        self.sftp = paramiko.SFTPClient.from_transport(transport)

    def disconnect(self):
        self.sftp.close()

    def sync(self):
        self._prepare()
        self.connect()
        # TODO: sftp.chdir()

        # TODO: use committed field of cpath row to indicate that an operation was performed successfully.

        while self._cpath_sync_tasks:
            cpath_task = self._cpath_sync_tasks.pop()
            action = cpath_task.action
            cpath = cpath_task.cpath

            if action == 'DELETE':
                if cpath.is_dir():
                    self.sftp.rmdir(cpath.path)
                else:
                    self.sftp.remove(cpath.path)
                self.notify_cpath_deleted(cpath)
            else:
                print(f"Putting: {cpath.name}")
                if cpath.is_dir():
                    self.sftp.mkdir(cpath.path)
                else:
                    self.sftp.put(os.path.join(self._project_base_path, cpath.path), cpath.path)
                self.notify_cpath_uploaded(cpath)
            if self._pause:
                self.notify_sync_paused(f'Sync paused, tasks incomplete: {len(self._cpath_sync_tasks)}')
                return
        self.sftp.close()
        self.notify_sync_completed('Sync complete')
