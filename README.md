# pico_weather

Raspberry pi pico W based weather station.

Measures various weather (wind speed and direction, temperature, pressure, humidity, rainfall),  environmental (dew point, light intensity) and system (battery voltage and status, free memory) variables and pushes readings via MQTT. 

Works with the following sensors:

- Adafruit BME280 temperature, pressure and humidity sensor
- Adafruit Veml7700 light sensor
- Adafruit Max17048 LiPoly fuel gauge
- Pimoroni Anemometer, wind vane and rain gauge

MQTT messages captured via Node-Red and visualised in Grafana.

Adafruit CircuitPython 8.0.5 on 2023-03-31; Raspberry Pi Pico W with rp2040


