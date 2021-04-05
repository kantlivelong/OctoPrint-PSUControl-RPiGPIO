# coding=utf-8
from __future__ import absolute_import

__author__ = "Shawn Bruce <kantlivelong@gmail.com>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2021 Shawn Bruce - Released under terms of the AGPLv3 License"

import octoprint.plugin

class PSUControl_RPiGPIO(octoprint.plugin.StartupPlugin,
                         octoprint.plugin.TemplatePlugin,
                         octoprint.plugin.SettingsPlugin):

    def __init__(self):
        self._pin_to_gpio_rev1 = [-1, -1, -1, 0, -1, 1, -1, 4, 14, -1, 15, 17, 18, 21, -1, 22, 23, -1, 24, 10, -1, 9, 25, 11, 8, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1 ]
        self._pin_to_gpio_rev2 = [-1, -1, -1, 2, -1, 3, -1, 4, 14, -1, 15, 17, 18, 27, -1, 22, 23, -1, 24, 10, -1, 9, 25, 11, 8, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1 ]
        self._pin_to_gpio_rev3 = [-1, -1, -1, 2, -1, 3, -1, 4, 14, -1, 15, 17, 18, 27, -1, 22, 23, -1, 24, 10, -1, 9, 25, 11, 8, -1, 7, -1, -1, 5, -1, 6, 12, 13, -1, 19, 16, 26, 20, -1, 21 ]

        self.config = dict()

        self._configuredGPIOPins = []


    def get_settings_defaults(self):
        return dict(
            GPIOMode = 'BOARD',
            onoffGPIOPin = 0,
            invertonoffGPIOPin = False,
            senseGPIOPin = 0,
            invertsenseGPIOPin = False,
            senseGPIOPinPUD = ''
        )


    def on_settings_initialized(self):
        self.reload_settings()


    def reload_settings(self):
        for k, v in self.get_settings_defaults().items():
            if isinstance(v, str):
                v = self._settings.get([k])
            elif isinstance(v, bool):
                v = self._settings.get_boolean([k])
            elif isinstance(v, int):
                v = self._settings.get_int([k])

            self.config[k] = v
            self._logger.debug("{}: {}".format(k, v))


    def on_startup(self, host, port):
        try:
            global GPIO
            import RPi.GPIO as GPIO

            self._logger.info("Running RPi.GPIO version {}".format(GPIO.VERSION))
            if GPIO.VERSION < "0.6":
                self._logger.error("RPi.GPIO version 0.6.0 or greater required.")
                return
        except NameError:
            self._logger.error("RPi.GPIO not detected. Plugin will not be registered with PSUControl.")
            return

        psucontrol_helpers = self._plugin_manager.get_helpers("psucontrol")
        if 'register_plugin' not in psucontrol_helpers.keys():
            self._logger.warning("The version of PSUControl that is installed does not support plugin registration.")
            return

        self._logger.debug("Registering plugin with PSUControl")
        psucontrol_helpers['register_plugin'](self)


    def _gpio_board_to_bcm(self, pin):
        if GPIO.RPI_REVISION == 1:
            pin_to_gpio = self._pin_to_gpio_rev1
        elif GPIO.RPI_REVISION == 2:
            pin_to_gpio = self._pin_to_gpio_rev2
        else:
            pin_to_gpio = self._pin_to_gpio_rev3

        return pin_to_gpio[pin]


    def _gpio_bcm_to_board(self, pin):
        if GPIO.RPI_REVISION == 1:
            pin_to_gpio = self._pin_to_gpio_rev1
        elif GPIO.RPI_REVISION == 2:
            pin_to_gpio = self._pin_to_gpio_rev2
        else:
            pin_to_gpio = self._pin_to_gpio_rev3

        return pin_to_gpio.index(pin)


    def _gpio_get_pin(self, pin):
        if (GPIO.getmode() == GPIO.BOARD and self.config['GPIOMode'] == 'BOARD') or (GPIO.getmode() == GPIO.BCM and self.config['GPIOMode'] == 'BCM'):
            return pin
        elif GPIO.getmode() == GPIO.BOARD and self.config['GPIOMode'] == 'BCM':
            return self._gpio_bcm_to_board(pin)
        elif GPIO.getmode() == GPIO.BCM and self.config['GPIOMode'] == 'BOARD':
            return self._gpio_board_to_bcm(pin)
        else:
            return 0


    def setup(self):
        GPIO.setwarnings(False)

        if GPIO.getmode() is None:
            if self.config['GPIOMode'] == 'BOARD':
                GPIO.setmode(GPIO.BOARD)
            elif self.config['GPIOMode'] == 'BCM':
                GPIO.setmode(GPIO.BCM)
            else:
                return

        if self.config['onoffGPIOPin'] > 0:
            self._logger.info("Configuring GPIO for pin {}".format(self.config['onoffGPIOPin']))
            try:
                if not self.config['invertonoffGPIOPin']:
                    initial_pin_output=GPIO.LOW
                else:
                    initial_pin_output=GPIO.HIGH

                GPIO.setup(self._gpio_get_pin(self.config['onoffGPIOPin']), GPIO.OUT, initial=initial_pin_output)
                self._configuredGPIOPins.append(self.config['onoffGPIOPin'])
            except (RuntimeError, ValueError) as e:
                self._logger.error(e)

        if self.config['senseGPIOPin'] > 0:
            self._logger.info("Configuring GPIO for pin {}".format(self.config['senseGPIOPin']))

            if self.config['senseGPIOPinPUD'] == 'PULL_UP':
                pull_up_down = GPIO.PUD_UP
            elif self.config['senseGPIOPinPUD'] == 'PULL_DOWN':
                pull_up_down = GPIO.PUD_DOWN
            else:
                pull_up_down = GPIO.PUD_OFF

            try:
                GPIO.setup(self._gpio_get_pin(self.config['senseGPIOPin']), GPIO.IN, pull_up_down=pull_up_down)
                self._configuredGPIOPins.append(self.config['senseGPIOPin'])
            except (RuntimeError, ValueError) as e:
                self._logger.error(e)


    def cleanup(self):
        GPIO.setwarnings(False)

        for pin in self._configuredGPIOPins:
            self._logger.debug("Cleaning up pin {}".format(pin))
            try:
                GPIO.cleanup(self._gpio_get_pin(pin))
            except (RuntimeError, ValueError) as e:
                self._logger.error(e)
        self._configuredGPIOPins = []


    def turn_psu_on(self):
        if self.config['onoffGPIOPin'] <= 0:
            return

        self._logger.debug("Switching PSU On Using GPIO: {}".format(self.config['onoffGPIOPin']))
        if not self.config['invertonoffGPIOPin']:
            o = GPIO.HIGH
        else:
            o = GPIO.LOW

        try:
            GPIO.output(self._gpio_get_pin(self.config['onoffGPIOPin']), o)
        except (RuntimeError, ValueError) as e:
            self._logger.error(e)


    def turn_psu_off(self):
        if self.config['onoffGPIOPin'] <= 0:
            return

        self._logger.debug("Switching PSU Off Using GPIO: {}".format(self.config['onoffGPIOPin']))
        if self.config['invertonoffGPIOPin']:
            o = GPIO.HIGH
        else:
            o = GPIO.LOW

        try:
            GPIO.output(self._gpio_get_pin(self.config['onoffGPIOPin']), o)
        except (RuntimeError, ValueError) as e:
            self._logger.error(e)


    def get_psu_state(self):
        if self.config['senseGPIOPin'] <= 0:
            return 0

        r = 0
        try:
            r = GPIO.input(self._gpio_get_pin(self.config['senseGPIOPin']))
        except (RuntimeError, ValueError) as e:
            self._logger.error(e)
            return False
        self._logger.debug("Result: {}".format(r))
        r = bool(r)

        if self.config['invertsenseGPIOPin']:
            r = not r

        return r


    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.reload_settings()


    def get_settings_version(self):
        return 1


    def on_settings_migrate(self, target, current=None):
        pass


    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False)
        ]


    def get_update_information(self):
        return dict(
            psucontrol=dict(
                displayName="PSU Control - RPi.GPIO",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="kantlivelong",
                repo="OctoPrint-PSUControl-RPiGPIO",
                current=self._plugin_version,

                # update method: pip w/ dependency links
                pip="https://github.com/kantlivelong/OctoPrint-PSUControl-RPiGPIO/archive/{target_version}.zip"
            )
        )

__plugin_name__ = "PSU Control - RPi.GPIO"
__plugin_pythoncompat__ = ">=2.7,<4"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = PSUControl_RPiGPIO()