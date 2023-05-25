# pico_weather

Raspberry pi pico W based solar powered weather station.

Measures various weather (wind speed and direction, temperature, pressure, humidity, rainfall),  environmental (dew point, light intensity) and system (battery voltage and status, free memory) variables and pushes readings via MQTT. 

Works with the following sensors:

- [Adafruit BME280](https://www.adafruit.com/product/2652) temperature, pressure and humidity sensor
- [Adafruit Veml7700](https://learn.adafruit.com/adafruit-veml7700/overview) light sensor
- [Adafruit Max17048](https://www.adafruit.com/product/5580) LiPoly fuel gauge
- [Sparkfun](https://www.sparkfun.com/products/15901) anemometer, wind vane and rain gauge


MQTT messages captured via Node-Red and visualised in Grafana.

Adafruit CircuitPython 8.0.5 2023-03-31; Raspberry Pi Pico W with rp2040


