// Author: Steffen Frahm, ksf@hst.aau.dk
hw_timer_t* timer = NULL;

//#define number_of_channels 2
#define BAUDRATE 921600
uint8_t channels[] = { 2, 15, 13, 12 };
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
  timerAlarm(timer, 1000, true, 0);
}

void loop() {
  delay(1);  // just to make sure that loop does something
}