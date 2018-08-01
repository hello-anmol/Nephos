"""
Checks the NephosConfig (github.com/thealphadollar/NephosConfig) repository for change
in data and updates accordingly.
"""
import os
import urllib.request
from shutil import copy2
from logging import getLogger
import filecmp

from .checker import Checker
from .. import __nephos_dir__, __config_dir__
from ..exceptions import UpdateDataFailure
from ..load_config import Config
from ..recorder.channels import ChannelHandler
from ..preprocessor.share_handler import ShareHandler


LOG = getLogger(__name__)
NEW_DATA = os.path.join(__nephos_dir__, "add_data.yaml")
NEW_JOBS = os.path.join(__nephos_dir__, "add_jobs.yaml")
CURRENT_DATA = os.path.join(__config_dir__, "add_data.yaml")
CURRENT_JOBS = os.path.join(__config_dir__, "add_jobs.yaml")


class UpdateData(Checker):
    """
    Syncs the current data with the aforementioned repositories data
    """
    def __init__(self, config_maintain, job_handler):
        """
        Initiates UpdateData

        Parameters
        ----------
        config_maintain
            type: dict
            contains the essential configuration required to run
        job_handler
        """
        super(UpdateData, self).__init__(config_maintain)
        self.add_data_url = self._get_data("update_data", "add_data")
        self.add_jobs_url = self._get_data("update_data", "add_jobs")
        self.job_handler = job_handler

    def _execute(self):
        """
        Runs downloading, checking and populating the database with new data.

        Returns
        -------

        """

        try:
            self._download_files()
            LOG.debug("Downloaded config files.")
            data, jobs = self._compare()
            if data:
                LOG.debug("Updating channels and share lists ...")
                self._update("data")
            if jobs:
                LOG.debug("Updating jobs ...")
                self._update("jobs")
            self._remove_new_files()
            if data or jobs:
                msg_type = "update_success"
                msg = "New configuration loaded into Nephos successfully."
                self._handle(True, msg_type, msg)

        except UpdateDataFailure:
            msg_type = "update_failed"
            msg = "Updating configuration failed. Please check if you have " \
                  "followed the right format.\nCheck logs and report if the issue persists."
            self._handle(True, msg_type, msg)

    def _download_files(self):
        """
        Downloads the new configuration files from the aforementioned github repository.

        Returns
        -------

        """
        try:
            urllib.request.urlretrieve(self.add_data_url, NEW_DATA)
            urllib.request.urlretrieve(self.add_jobs_url, NEW_JOBS)
        except Exception as err:
            LOG.debug(err)
            raise UpdateDataFailure()

    @staticmethod
    def _compare():
        """
        Compares newly downloaded files with previous ones to see if there is any change.

        Returns
        -------
        type: bool
        True if add_data.yaml has changed, False otherwise
        type: bool

        """
        data_file = filecmp.cmp(NEW_DATA, CURRENT_DATA)
        jobs_file = filecmp.cmp(NEW_JOBS, CURRENT_JOBS)

        return data_file, jobs_file

    def _update(self, data_type):
        """
        Updates the old data files after populating the database with new data

        Parameters
        ----------
        data_type
            type: str
            whether the data to be updated is channels or jobs

        Returns
        -------

        """
        if data_type == "data":
            data = Config.load_data(NEW_DATA, False)
        elif data_type == "jobs":
            data = Config.load_data(NEW_JOBS, False)
        else:
            raise UpdateDataFailure()

        if data:

            if data_type == "data":
                try:
                    if data["channels"] is not None:
                        ChannelHandler.insert_channels(data["channels"])
                    else:
                        LOG.warning("No channels found!")
                except KeyError as error:
                    LOG.warning("No channel data found!")
                    LOG.debug(error)
                try:
                    if data["sharing_entity"] is not None:
                        ShareHandler.insert_share_entities(data["sharing_entity"])
                    else:
                        LOG.warning("No share entity found!")
                except KeyError as error:
                    LOG.warning("No share entity found!")
                    LOG.debug(error)

                copy2(NEW_DATA, CURRENT_DATA)

            if data_type == "jobs":
                if self.job_handler.load_jobs(data):
                    copy2(NEW_JOBS, CURRENT_JOBS)
                else:
                    raise UpdateDataFailure()

        else:
            raise UpdateDataFailure()

    @staticmethod
    def _remove_new_files():
        """
        Post comparison (and maybe updating old data), the newly downloaded
        files are removed

        Returns
        -------

        """
        os.remove(NEW_DATA)
        os.remove(NEW_JOBS)