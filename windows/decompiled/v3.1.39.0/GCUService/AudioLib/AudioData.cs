using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using LightingModel;
using NAudio.CoreAudioApi;
using NAudio.Wave;

namespace AudioLib;

internal class AudioData
{
	public delegate void WaveOutDataBufferDelegate(object sender);

	private static readonly AudioData adudiomodel = new AudioData();

	private bool KeyboardSwitch;

	private bool LightbarSwitch;

	private RGB_S[] KeyboardColorBurffer;

	private RGB_S[] LightbarColorBuffer;

	private int RATE = 44100;

	private int BUFFERSIZE = (int)Math.Pow(2.0, 11.0);

	private WaveOutEvent waveoutEvent = new WaveOutEvent();

	public BufferedWaveProvider bwp;

	private MMDeviceEnumerator enumerator;

	private MMDevice WaveInDevice;

	private List<float> MeterBuffer = new List<float>();

	private List<float> MeterBuffer_L = new List<float>();

	private List<float> MeterBuffer_R = new List<float>();

	private bool WaveOutSwtich;

	private bool WaveInSwtich;

	private int meterDistruct = 1;

	private object WaveoutLock = new object();

	private static Stopwatch sw = new Stopwatch();

	private SemaphoreSlim SettingsemporeSlim = new SemaphoreSlim(1, 1);

	private Stopwatch stopwatch = new Stopwatch();

	public static AudioData Instance => adudiomodel;

	public int TimeOut { get; set; } = 20;

	public int DelayTime { get; set; } = 1;

	public float EveryDelayTime { get; set; } = 1f;

	public int ColumNumbers { get; set; } = 19;

	public double RegressMeter { get; set; } = 1.3;

	public MUSICTYPE MusicType { get; set; }

	public float Speed { get; set; } = 1f;

	public byte AudioLight { get; set; } = 50;

	public RGB_S[] ColorBuffer { get; set; }

	public event WaveOutDataBufferDelegate WaveOutEventHandler;

	public event WaveOutDataBufferDelegate KeyBoardWaveOutEventHandler;

	public event WaveOutDataBufferDelegate KeyBoardWaveLeftRightOutEventHandler;

	public event WaveOutDataBufferDelegate KeyBoardWaveCenterLeftRightOutEventHandler;

	public event WaveOutDataBufferDelegate KeyBoardWaveBrightnessEventHandler;

	public event WaveOutDataBufferDelegate LightbarEventHandler;

	public event WaveOutDataBufferDelegate WaveInEventHandler;

	public event EventHandler InputDeviceMuteEvent;

	private AudioData()
	{
	}

	public void InitInputDevice()
	{
		enumerator = new MMDeviceEnumerator();
		MMDeviceCollection mMDeviceCollection = enumerator.EnumerateAudioEndPoints(DataFlow.Capture, DeviceState.Active | DeviceState.Disabled);
		if (mMDeviceCollection.Count > 0)
		{
			WaveInDevice = mMDeviceCollection.First();
			WaveInDevice.AudioEndpointVolume.OnVolumeNotification += AudioEndpointVolume_OnVolumeNotification;
		}
	}

	private void AudioEndpointVolume_OnVolumeNotification(AudioVolumeNotificationData data)
	{
		this.InputDeviceMuteEvent(data.Muted, null);
	}

	public void SetInputDeviceMute(bool Enable)
	{
		foreach (MMDevice item in this.enumerator.EnumerateAudioEndPoints(DataFlow.Capture, DeviceState.Active))
		{
			item.AudioEndpointVolume.Mute = Enable;
		}
	}

	public bool GetInputDeviceMute()
	{
		return WaveInDevice.AudioEndpointVolume.Mute;
	}

	private List<float> RegressKeyboardData(List<float> meterBuffer)
	{
		List<float> list = new List<float>();
		for (int i = 0; i < meterBuffer.Count; i++)
		{
			double y = RegressMeter + (double)(Speed * 0.1f);
			float item = Convert.ToSingle(Math.Pow(meterBuffer[i] * 10f, y)) / 2f;
			list.Add(item);
		}
		return list;
	}

	private List<float> RegressKeyboardPcakDataStereo(List<float> MeterbufferL, List<float> MeterbufferR)
	{
		if (MeterbufferL.Count > 0)
		{
			List<float> list = new List<float>();
			List<float> list2 = new List<float>();
			for (int i = 0; i < MeterbufferL.Count; i++)
			{
				double y = RegressMeter + (double)(Speed * 0.1f + 0.1f);
				float item = Convert.ToSingle(Math.Pow(MeterbufferL[i] * 10f, y)) / 2f;
				list2.Add(item);
			}
			List<float> list3 = new List<float>();
			for (int j = 0; j < MeterbufferR.Count; j++)
			{
				double y2 = RegressMeter + (double)(Speed * 0.1f + 0.1f);
				float item2 = Convert.ToSingle(Math.Pow(MeterbufferR[j] * 10f, y2)) / 2f;
				list3.Add(item2);
			}
			if (list2.Count > 9)
			{
				list.AddRange((from n in list2.Take(10)
					orderby n
					select n).ToList());
				list.AddRange((from n in list3.Take(9)
					orderby n
					select n).ToList());
			}
			else
			{
				list.AddRange(list2.OrderBy((float n) => n).ToList());
				list.AddRange(list3.OrderBy((float n) => n).ToList());
			}
			return list;
		}
		return new List<float>();
	}

	private List<float> RegressKeyboardPackData(List<float> meterBuffer)
	{
		if (meterBuffer.Count > 0)
		{
			List<float> list = new List<float>();
			for (int i = 0; i < meterBuffer.Count; i++)
			{
				double y = RegressMeter + (double)(Speed * 0.1f + 0.1f);
				float item = Convert.ToSingle(Math.Pow(meterBuffer[i] * 10f, y)) / 2f;
				list.Add(item);
			}
			List<float> list2 = list.OrderBy((float n) => n).ToList();
			List<float> list3 = list.OrderByDescending((float n) => n).ToList();
			List<float> list4 = new List<float>();
			for (int num = 0; num < list2.Count / 2; num++)
			{
				list4.Add(list2[num]);
			}
			float item2 = list.Max();
			list4.Add(item2);
			list4.Add(item2);
			for (int num2 = list3.Count / 3; num2 < list3.Count; num2++)
			{
				list4.Add(list3[num2]);
			}
			return list4;
		}
		return new List<float>();
	}

	public void SetParam()
	{
		switch (MusicType)
		{
		case MUSICTYPE.NORMAL:
			RegressMeter = 1.3;
			break;
		case MUSICTYPE.STEREO:
			RegressMeter = 1.3;
			break;
		case MUSICTYPE.LEFTRIGHTSTEREO:
			RegressMeter = 1.5;
			break;
		case MUSICTYPE.CENTERLEFTRIGHTSTEREO:
			RegressMeter = 1.5;
			break;
		default:
			RegressMeter = 1.3;
			break;
		}
	}

	internal double percentile(double[] sortedData, double p)
	{
		if (p >= 100.0)
		{
			return sortedData[sortedData.Length - 1];
		}
		double num = (double)(sortedData.Length + 1) * p / 100.0;
		double num2 = 0.0;
		double num3 = 0.0;
		double num4 = p / 100.0 * (double)(sortedData.Length - 1) + 1.0;
		if (num >= 1.0)
		{
			num2 = sortedData[(int)Math.Floor(num4) - 1];
			num3 = sortedData[(int)Math.Floor(num4)];
		}
		else
		{
			num2 = sortedData[0];
			num3 = sortedData[1];
		}
		if (num2 == num3)
		{
			return num2;
		}
		double num5 = num4 - Math.Floor(num4);
		return num2 + num5 * (num3 - num2);
	}

	private void MeterBufferProcess(List<float> buffer, int colnumbers)
	{
		List<double> list = new List<double>();
		foreach (float item2 in buffer)
		{
			list.Add(item2);
		}
		if (buffer.Count < colnumbers && buffer.Count > 0)
		{
			float item = 0f;
			if (list.Count > 1)
			{
				item = Convert.ToSingle(percentile(list.OrderByDescending((double n) => n).ToArray(), 75.0));
			}
			int num = ColumNumbers - buffer.Count;
			for (int num2 = 0; num2 < num; num2++)
			{
				buffer.Add(item);
			}
		}
		else if (buffer.Count > colnumbers)
		{
			int num3 = buffer.Count - colnumbers;
			for (int num4 = 0; num4 < num3; num4++)
			{
				buffer.RemoveAt(0);
			}
		}
		float num5 = 0f;
		if (list.Count > 1)
		{
			num5 = Convert.ToSingle(list.Max() * 0.6);
		}
		for (int num6 = 0; num6 < buffer.Count; num6++)
		{
			if (buffer[num6] < num5)
			{
				buffer[num6] = num5;
			}
		}
	}

	private void ShowWavePackTick(MMDevice WaveOutDevice)
	{
		while (WaveOutSwtich)
		{
			sw.Reset();
			sw.Start();
			if (WaveOutDevice == null)
			{
				continue;
			}
			float num = 0f;
			while (true)
			{
				try
				{
					int count = WaveOutDevice.AudioMeterInformation.PeakValues.Count;
					float item2;
					float item = (item2 = WaveOutDevice.AudioMeterInformation.MasterPeakValue);
					if (count >= 2)
					{
						item2 = WaveOutDevice.AudioMeterInformation.PeakValues[0];
						item = WaveOutDevice.AudioMeterInformation.PeakValues[1];
					}
					for (int i = 0; i < meterDistruct; i++)
					{
						MeterBuffer.Add(item2);
						MeterBuffer.Add(item);
						MeterBuffer_L.Add(item2);
						MeterBuffer_R.Add(item);
					}
					if (MeterBuffer.Count >= ColumNumbers || num > (float)TimeOut)
					{
						break;
					}
					num += 1f;
					continue;
				}
				catch (Exception)
				{
					continue;
				}
			}
			Thread.Sleep(DelayTime);
			sw.Stop();
			if (sw.ElapsedMilliseconds >= TimeOut)
			{
				meterDistruct = Convert.ToInt32(2);
			}
			else
			{
				meterDistruct = 1;
			}
			MeterBufferProcess(MeterBuffer, ColumNumbers);
			MeterBufferProcess(MeterBuffer_L, ColumNumbers / 2);
			MeterBufferProcess(MeterBuffer_R, ColumNumbers / 2);
			if (this.WaveOutEventHandler != null)
			{
				this.WaveOutEventHandler?.Invoke(MeterBuffer);
			}
			if (MusicType == MUSICTYPE.NORMAL && this.KeyBoardWaveOutEventHandler != null)
			{
				ColumNumbers = 19;
				List<float> sender = RegressKeyboardPackData(MeterBuffer);
				this.KeyBoardWaveOutEventHandler?.Invoke(sender);
			}
			if (MusicType == MUSICTYPE.STEREO && this.KeyBoardWaveOutEventHandler != null)
			{
				if (MeterBuffer_R.Count > 0)
				{
					MeterBuffer_R.Add(MeterBuffer.Last());
				}
				List<float> sender2 = RegressKeyboardPcakDataStereo(MeterBuffer_L, MeterBuffer_R);
				this.KeyBoardWaveOutEventHandler?.Invoke(sender2);
			}
			if (MusicType == MUSICTYPE.LEFTRIGHTSTEREO && this.KeyBoardWaveLeftRightOutEventHandler != null)
			{
				List<float> sender3 = RegressKeyboardPcakDataStereo(MeterBuffer_L, MeterBuffer_R);
				this.KeyBoardWaveLeftRightOutEventHandler?.Invoke(sender3);
			}
			if (MusicType == MUSICTYPE.CENTERLEFTRIGHTSTEREO && this.KeyBoardWaveCenterLeftRightOutEventHandler != null)
			{
				List<float> sender4 = RegressKeyboardPcakDataStereo(MeterBuffer_R, MeterBuffer_L);
				this.KeyBoardWaveCenterLeftRightOutEventHandler?.Invoke(sender4);
			}
			if (MusicType == MUSICTYPE.BRIGHTNESS && this.KeyBoardWaveBrightnessEventHandler != null)
			{
				List<float> sender5 = RegressKeyboardPcakDataStereo(MeterBuffer_L, MeterBuffer_R);
				this.KeyBoardWaveBrightnessEventHandler?.Invoke(sender5);
			}
			if (MusicType == MUSICTYPE.BRIGHTNESS && this.LightbarEventHandler != null)
			{
				List<float> sender6 = RegressKeyboardPcakDataStereo(MeterBuffer_L, MeterBuffer_R);
				this.LightbarEventHandler?.Invoke(sender6);
			}
			MeterBuffer.Clear();
			MeterBuffer_L.Clear();
			MeterBuffer_R.Clear();
			if (MeterBuffer.Count > ColumNumbers)
			{
				MeterBuffer.Clear();
				MeterBuffer_L.Clear();
				MeterBuffer_R.Clear();
			}
			if (!WaveOutSwtich)
			{
				break;
			}
		}
	}

	public async void WaveOutAudioStart(int deviceNumber = -1)
	{
		try
		{
			RunTask(deviceNumber);
		}
		catch
		{
		}
	}

	public void ReleaseSemaphoreSlimByMenual()
	{
		SettingsemporeSlim.Release();
	}

	private async void RunTask(int deviceNumber = -1)
	{
		await SettingsemporeSlim.WaitAsync();
		try
		{
			await Task.Run(delegate
			{
				if (!WaveOutSwtich)
				{
					WaveOutSwtich = true;
					MMDeviceCollection mMDeviceCollection = enumerator?.EnumerateAudioEndPoints(DataFlow.Render, DeviceState.Active);
					if (mMDeviceCollection != null && mMDeviceCollection.Count > 0)
					{
						if (deviceNumber != -1)
						{
							ShowWavePackTick(mMDeviceCollection[deviceNumber]);
						}
						else
						{
							int num = 0;
							stopwatch.Start();
							while (!(mMDeviceCollection[num].AudioMeterInformation.MasterPeakValue > 0f))
							{
								num++;
								if (mMDeviceCollection.Count == num)
								{
									num = 0;
								}
								Thread.Sleep(1000);
							}
							SetParam();
							MeterBuffer.Clear();
							MeterBuffer_L.Clear();
							MeterBuffer_R.Clear();
							ShowWavePackTick(mMDeviceCollection[num]);
						}
					}
				}
			});
		}
		catch
		{
		}
		finally
		{
			SettingsemporeSlim.Release();
		}
	}

	public bool GetKeyboardSwitch()
	{
		return KeyboardSwitch;
	}

	public bool GetLighbarSwitch()
	{
		return LightbarSwitch;
	}

	public RGB_S[] GetKeyboardColor()
	{
		return KeyboardColorBurffer;
	}

	public RGB_S[] GetLightbarColor()
	{
		return LightbarColorBuffer;
	}

	public void SetKeyboardSwitch(bool enable, RGB_S[] ColorBuffer)
	{
		KeyboardColorBurffer = ColorBuffer;
		KeyboardSwitch = enable;
	}

	public void SetLightbarSwitch(bool enable, RGB_S[] ColorBuffer)
	{
		LightbarColorBuffer = ColorBuffer;
		LightbarSwitch = enable;
	}

	public void WaveOutAudioStop()
	{
		if (!KeyboardSwitch && !LightbarSwitch)
		{
			WaveOutSwtich = false;
			MeterBuffer.Clear();
			MeterBuffer_L.Clear();
			MeterBuffer_R.Clear();
			WaveInDevice = null;
		}
		if (!KeyboardSwitch)
		{
			this.KeyBoardWaveOutEventHandler = null;
			this.KeyBoardWaveLeftRightOutEventHandler = null;
			this.KeyBoardWaveCenterLeftRightOutEventHandler = null;
			this.KeyBoardWaveBrightnessEventHandler = null;
		}
		if (!LightbarSwitch)
		{
			this.LightbarEventHandler = null;
		}
	}

	public void WaveInAudioStart()
	{
		StartListeningToMicrophone();
		WaveInSwtich = true;
		WaveInTimer_Tick();
	}

	private void StartListeningToMicrophone(int audioDevice = 0)
	{
		WaveIn waveIn = new WaveIn();
		waveIn.DeviceNumber = audioDevice;
		waveIn.WaveFormat = new WaveFormat(RATE, 1);
		waveIn.BufferMilliseconds = (int)((double)BUFFERSIZE / (double)RATE * 1000.0);
		waveIn.DataAvailable += AudioDataAvailable;
		bwp = new BufferedWaveProvider(waveIn.WaveFormat);
		bwp.BufferLength = BUFFERSIZE * 2;
		bwp.DiscardOnBufferOverflow = true;
		try
		{
			waveIn.StartRecording();
		}
		catch
		{
			string.Concat("Could not record from audio device!\n\n" + "Is your microphone plugged in?\n", "Is it set as your default recording device?");
		}
	}

	private void WaveInTimer_Tick()
	{
		while (WaveInSwtich)
		{
			int bUFFERSIZE = BUFFERSIZE;
			byte[] array = new byte[bUFFERSIZE];
			bwp.Read(array, 0, bUFFERSIZE);
			if (array.Length == 0 || array[bUFFERSIZE - 2] == 0)
			{
				break;
			}
			int num = 2;
			int num2 = array.Length / num;
			double[] array2 = new double[num2];
			double[] array3 = new double[num2];
			_ = new double[num2 / 2];
			for (int i = 0; i < num2; i++)
			{
				short num3 = BitConverter.ToInt16(array, i * 2);
				array2[i] = (double)num3 / Math.Pow(2.0, 16.0) * 200.0;
			}
			array3 = FFT(array2);
			double num4 = GoertzelFilter(array3, 2000.0, 0, array3.Count());
			Console.WriteLine(num4);
			if (this.WaveInEventHandler != null)
			{
				this.WaveInEventHandler(new
				{
					PCM = array2,
					FFT = array3,
					Filter = num4
				});
			}
			Thread.Sleep(1);
		}
	}

	private double GoertzelFilter(double[] samples, double freq, int start, int end)
	{
		double num = 0.0;
		double num2 = 0.0;
		double num3 = freq / (double)RATE;
		double num4 = 2.0 * Math.Cos(Math.PI * 2.0 * num3);
		for (int i = start; i < end; i++)
		{
			double num5 = samples[i] + num4 * num - num2;
			num2 = num;
			num = num5;
		}
		return num2 * num2 + num * num - num4 * num * num2;
	}

	private void AudioDataAvailable(object sender, WaveInEventArgs e)
	{
		bwp.AddSamples(e.Buffer, 0, e.BytesRecorded);
	}

	public double[] FFT(double[] data)
	{
		return new double[data.Length];
	}

	public void WaveInAudioStop()
	{
		WaveInSwtich = false;
	}

	public List<string> GetWaveInDevice()
	{
		List<string> list = new List<string>();
		foreach (MMDevice item in this.enumerator.EnumerateAudioEndPoints(DataFlow.Capture, DeviceState.Active))
		{
			list.Add(item.DeviceFriendlyName);
		}
		return list;
	}

	public List<string> GetWaveOutDevice()
	{
		List<string> list = new List<string>();
		foreach (MMDevice item in this.enumerator.EnumerateAudioEndPoints(DataFlow.Render, DeviceState.Active))
		{
			list.Add(item.DeviceFriendlyName);
		}
		return list;
	}
}
