import functools
import json
import os
from datetime import datetime
from multiprocessing import Queue
from uuid import uuid4
from requests.exceptions import HTTPError, ConnectionError

# On Windows the monkeypatching of `run_real` below doesn't work like on Linux
# This has the side effect of emitting the UIUpdate in DownloadThread complaining with a TypeError
# So import `legendary.core` and monkeypatch its imported DLManager
import legendary.core
from legendary.core import LegendaryCore as LegendaryCoreReal
from legendary.lfs.utils import delete_folder
from legendary.models.downloading import AnalysisResult
from legendary.models.egl import EGLManifest
from legendary.models.exceptions import InvalidCredentialsError
from legendary.models.game import Game, InstalledGame
from legendary.models.manifest import ManifestMeta

from rare.lgndr.downloader.mp.manager import DLManager
from rare.lgndr.glue.exception import LgndrException, LgndrCoreLogHandler

legendary.core.DLManager = DLManager


# fmt: off
class LegendaryCore(LegendaryCoreReal):

    def __init__(self, override_config=None, timeout=10.0):
        super(LegendaryCore, self).__init__(override_config=override_config, timeout=timeout)
        self.handler = LgndrCoreLogHandler()
        self.log.addHandler(self.handler)

    @staticmethod
    def unlock_installed(func):
        @functools.wraps(func)
        def unlock(self, *args, **kwargs):
            ret = func(self, *args, **kwargs)
            self.lgd._installed_lock.release(force=True)
            return ret
        return unlock

    def _login(self, lock, force_refresh=False) -> bool:
        """
        Attempts logging in with existing credentials.

        raises ValueError if no existing credentials or InvalidCredentialsError if the API return an error
        """
        if not lock.data:
            raise ValueError('No saved credentials')
        elif self.logged_in and lock.data['expires_at']:
            dt_exp = datetime.fromisoformat(lock.data['expires_at'][:-1])
            dt_now = datetime.utcnow()
            td = dt_now - dt_exp

            # if session still has at least 10 minutes left we can re-use it.
            if dt_exp > dt_now and abs(td.total_seconds()) > 600:
                return True
            else:
                self.logged_in = False

        # run update check
        if self.update_check_enabled():
            try:
                self.check_for_updates()
            except Exception as e:
                self.log.warning(f'Checking for Legendary updates failed: {e!r}')
        else:
            self.apply_lgd_config()

        # check for overlay updates
        if self.is_overlay_installed():
            try:
                self.check_for_overlay_updates()
            except Exception as e:
                self.log.warning(f'Checking for EOS Overlay updates failed: {e!r}')

        if lock.data['expires_at'] and not force_refresh:
            dt_exp = datetime.fromisoformat(lock.data['expires_at'][:-1])
            dt_now = datetime.utcnow()
            td = dt_now - dt_exp

            # if session still has at least 10 minutes left we can re-use it.
            if dt_exp > dt_now and abs(td.total_seconds()) > 600:
                self.log.info('Trying to re-use existing login session...')
                try:
                    self.egs.resume_session(lock.data)
                    self.logged_in = True
                    return True
                except InvalidCredentialsError as e:
                    self.log.warning(f'Resuming failed due to invalid credentials: {e!r}')
                except Exception as e:
                    self.log.warning(f'Resuming failed for unknown reason: {e!r}')
                # If verify fails just continue the normal authentication process
                self.log.info('Falling back to using refresh token...')

        try:
            self.log.info('Logging in...')
            userdata = self.egs.start_session(lock.data['refresh_token'])
        except InvalidCredentialsError:
            self.log.error('Stored credentials are no longer valid! Please login again.')
            lock.clear()
            return False
        except (HTTPError, ConnectionError) as e:
            self.log.error(f'HTTP request for login failed: {e!r}, please try again later.')
            return False

        lock.data = userdata
        self.logged_in = True
        return True

    # skip_sync defaults to false but since Rare is persistent, skip by default
    # def get_installed_game(self, app_name, skip_sync=True) -> InstalledGame:
    #     return super(LegendaryCore, self).get_installed_game(app_name, skip_sync)

    def prepare_download(self, game: Game, base_game: Game = None, base_path: str = '',
                         status_q: Queue = None, max_shm: int = 0, max_workers: int = 0,
                         force: bool = False, disable_patching: bool = False,
                         game_folder: str = '', override_manifest: str = '',
                         override_old_manifest: str = '', override_base_url: str = '',
                         platform: str = 'Windows', file_prefix_filter: list = None,
                         file_exclude_filter: list = None, file_install_tag: list = None,
                         dl_optimizations: bool = False, dl_timeout: int = 10,
                         repair: bool = False, repair_use_latest: bool = False,
                         disable_delta: bool = False, override_delta_manifest: str = '',
                         egl_guid: str = '', preferred_cdn: str = None,
                         disable_https: bool = False, bind_ip: str = None) -> (DLManager, AnalysisResult, ManifestMeta):
        dlm, analysis, igame = super(LegendaryCore, self).prepare_download(
            game=game, base_game=base_game, base_path=base_path,
            status_q=status_q, max_shm=max_shm, max_workers=max_workers,
            force=force, disable_patching=disable_patching,
            game_folder=game_folder, override_manifest=override_manifest,
            override_old_manifest=override_old_manifest, override_base_url=override_base_url,
            platform=platform, file_prefix_filter=file_prefix_filter,
            file_exclude_filter=file_exclude_filter, file_install_tag=file_install_tag,
            dl_optimizations=dl_optimizations, dl_timeout=dl_timeout,
            repair=repair, repair_use_latest=repair_use_latest,
            disable_delta=disable_delta, override_delta_manifest=override_delta_manifest,
            egl_guid=egl_guid, preferred_cdn=preferred_cdn,
            disable_https=disable_https, bind_ip=bind_ip,
        )
        # lk: monkeypatch run_real (the method that emits the stats) into DLManager
        # pylint: disable=E1111
        dlm.run_real = DLManager.run_real.__get__(dlm, DLManager)
        # lk: set the queue for reporting statistics back the UI
        dlm.status_queue = Queue()
        # lk: set the queue to send control signals to the DLManager
        # lk: this doesn't exist in the original class, but it is monkeypatched in
        dlm.signals_queue = Queue()
        return dlm, analysis, igame

    def uninstall_game(self, installed_game: InstalledGame, delete_files=True, delete_root_directory=False):
        try:
            super(LegendaryCore, self).uninstall_game(installed_game, delete_files, delete_root_directory)
        except Exception as e:
            raise e
        finally:
            pass

    @unlock_installed
    def egl_import(self, app_name):
        try:
            super(LegendaryCore, self).egl_import(app_name)
        except LgndrException as ret:
            raise ret
        finally:
            pass

    def egstore_write(self, app_name):
        self.log.debug(f'Exporting ".egstore" for "{app_name}"')
        # load igame/game
        lgd_game = self.get_game(app_name)
        lgd_igame = self._get_installed_game(app_name)
        manifest_data, _ = self.get_installed_manifest(app_name)
        if not manifest_data:
            self.log.error(f'Game Manifest for "{app_name}" not found, cannot export!')
            return

        # create guid if it's not set already
        if not lgd_igame.egl_guid:
            lgd_igame.egl_guid = str(uuid4()).replace('-', '').upper()
            _ = self._install_game(lgd_igame)
        # convert to egl manifest
        egl_game = EGLManifest.from_lgd_game(lgd_game, lgd_igame)

        # make sure .egstore folder exists
        egstore_folder = os.path.join(lgd_igame.install_path, '.egstore')
        if not os.path.exists(egstore_folder):
            os.makedirs(egstore_folder)

        # copy manifest and create mancpn file in .egstore folder
        with open(os.path.join(egstore_folder, f'{egl_game.installation_guid}.manifest', ), 'wb') as mf:
            mf.write(manifest_data)

        mancpn = dict(FormatVersion=0, AppName=app_name,
                      CatalogItemId=lgd_game.catalog_item_id,
                      CatalogNamespace=lgd_game.namespace)
        with open(os.path.join(egstore_folder, f'{egl_game.installation_guid}.mancpn', ), 'w') as mcpnf:
            json.dump(mancpn, mcpnf, indent=4, sort_keys=True)

    def egstore_delete(self, igame: InstalledGame, delete_files=True):
        self.log.debug(f'Removing ".egstore" for "{igame.app_name}"')
        if delete_files:
            delete_folder(os.path.join(igame.install_path, '.egstore'))

    @unlock_installed
    def egl_export(self, app_name):
        try:
            super(LegendaryCore, self).egl_export(app_name)
        except LgndrException as ret:
            raise ret
        finally:
            pass

    def prepare_overlay_install(self, path=None):
        dlm, analysis_result, igame = super(LegendaryCore, self).prepare_overlay_install(path)
        # lk: monkeypatch status_q (the queue for download stats)
        # pylint: disable=E1111
        dlm.run_real = DLManager.run_real.__get__(dlm, DLManager)
        # lk: set the queue for reporting statistics back the UI
        dlm.status_queue = Queue()
        # lk: set the queue to send control signals to the DLManager
        # lk: this doesn't exist in the original class, but it is monkeypatched in
        dlm.signals_queue = Queue()
        return dlm, analysis_result, igame

# fmt: on
