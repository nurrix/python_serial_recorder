// Author: Steffen Frahm, ksf@hst.aau.dk
hw_timer_t* timer = NULL;


/** baudrate must be larger than 
  BAUDRATE > MICROSECONDS_BETWEEN_SAMPLES * (number of channels) * 8 * 7 
  i.e. if we are using 2 channels, at 1ms sampling rate, the minimum baudrate we can use is 115200 
  These are the standard value options: 9600, 115200, 256000, 512000, 921600
 */
#define BAUDRATE 115200  // bits (not bytes) transfered per second.

#define MICROSECONDS_BETWEEN_SAMPLES 100000  // 1000 microseconds = 1 msec
uint8_t channels[] = { 2 };                // specify the gpio# where there is adc functionality.


/** DO NOT CHANGE ANYTHING BELOW HERE!!!!! */
int number_of_channels = sizeof(channels);
int* sensorValue = (int*)malloc(number_of_channels * sizeof(int));
short new_sample;

void IRAM_ATTR onTimer() {
  for (int i = 0; i < number_of_channels; i++) {
    sensorValue[i] = analogRead(channels[i]);
  }
  for (int i = 0; i < number_of_channels - 1; i++)  // run to N-1 channels (last channel needs println)
  {
    Serial.print(sensorValue[i]);
    Serial.print(" ");
  }
  Serial.println(sensorValue[number_of_channels - 1]);  // send last channel with line feed
}

void setup() {
  // put your setup code here, to run once:
  Serial.begin(BAUDRATE);       // Initialize the UART and set the baudrate
  delay(400);                   // Delay for letting the uart be ready for transmission
  timer = timerBegin(1000000);  // updaterate is 1.000.000 Hz
  timerAttachInterrupt(timer, &onTimer);
  timerAlarm(timer, MICROSECONDS_BETWEEN_SAMPLES, true, 0);
}

void loop() {
  delay(1);  // just to make sure that loop does something
}