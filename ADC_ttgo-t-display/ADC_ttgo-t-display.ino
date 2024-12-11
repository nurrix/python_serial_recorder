// Author: Steffen Frahm, ksf@hst.aau.dk 
hw_timer_t * timer = NULL;

#define number_of_channels 1
#define BAUDRATE 115200
uint8_t channels[number_of_channels] = {A0};//,A2,A3,A4,A5,A6,A7,A8,A9,A10,A11,A12,A13,A14,A15};



int sensorValue[number_of_channels];

bool SendData = false;

short new_sample;

void IRAM_ATTR onTimer(){
  serialEvent();

 if(SendData)
  {
    for (int i = 0; i < number_of_channels; i++) 
      {
        sensorValue[i] = analogRead(channels[i]);
      }
    for (int i = 0; i < number_of_channels - 1; i++) // run to N-1 channels (last channel needs println)
      { 
        Serial.print(sensorValue[i]);
        Serial.print(" ");
      }
    Serial.println(sensorValue[number_of_channels-1]); // send last channel with line feed
  }
}

void setup() {
  // put your setup code here, to run once:
  Serial.begin(BAUDRATE);       // Initialize the UART and set the baudrate 
  delay(400);                 // Delay for letting the uart be ready for transmission
  timer = timerBegin(1000000);
  timerAttachInterrupt(timer, &onTimer);
  timerAlarm(timer, 1000, true, 0);

}

void loop() {
  delay(100); // just to make sure that loop does something
}

void serialEvent()
{
 while (Serial.available())
  {
    int inChar = Serial.read();       // get the new byte
    switch (inChar)
    {
      case 's':
        SendData = true;
        break;
      case 'e':
        SendData = false;
        break;
      default:
        break;
    }
  }
}
