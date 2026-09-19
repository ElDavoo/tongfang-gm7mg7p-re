using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Runtime.InteropServices;

namespace MyControlCenter;

internal class FaceDetection
{
	private string Path = AppDomain.CurrentDomain.BaseDirectory + "face.bat";

	private OpenVinoService openVinoService = OpenVinoService.Instance;

	private MqttClientCtrl m_MQTTService = MqttClientCtrl.Instance;

	private const string Topic = "Openvino/Facedetection";

	private Dictionary<string, double> emotion = new Dictionary<string, double>();

	private static readonly FaceDetection _faceDetction = new FaceDetection();

	private Stopwatch sw = new Stopwatch();

	private string currentEmotion;

	public static FaceDetection Instance => _faceDetction;

	[DllImport("Powrprof.dll", CharSet = CharSet.Auto, ExactSpelling = true)]
	public static extern bool SetSuspendState(bool hiberate, bool forceCritical, bool disableWakeEvent);

	private FaceDetection()
	{
		emotion.Add("surprise", 0.0);
		emotion.Add("anger", 0.0);
		emotion.Add("happy", 0.0);
		emotion.Add("neutral", 1.0);
		emotion.Add("sad", 0.0);
	}

	public string getCurrentEmotion()
	{
		return currentEmotion;
	}

	public void Start()
	{
		openVinoService.Init(Path);
		openVinoService.Start();
		OpenVinoService obj = openVinoService;
		obj.OutputDataReceived = (DataReceivedEventHandler)Delegate.Combine(obj.OutputDataReceived, new DataReceivedEventHandler(Process_OutputDataReceived));
	}

	public void Stop()
	{
		openVinoService.Stop();
		OpenVinoService obj = openVinoService;
		obj.OutputDataReceived = (DataReceivedEventHandler)Delegate.Remove(obj.OutputDataReceived, new DataReceivedEventHandler(Process_OutputDataReceived));
		try
		{
			Process[] processesByName = Process.GetProcessesByName("interactive_face_detection_demo");
			for (int i = 0; i < processesByName.Count(); i++)
			{
				processesByName[i].Kill();
			}
		}
		catch
		{
		}
	}

	private void Process_OutputDataReceived(object sender, DataReceivedEventArgs e)
	{
		if (e.Data.Contains("NoFace"))
		{
			m_MQTTService.Publish("Openvino/Facedetection", new
			{
				Face = "NoFace"
			}, retain: false);
		}
		else if (e.Data.Contains("isMale"))
		{
			string[] array = e.Data.Split(',');
			double num = Convert.ToDouble(array[1]);
			double num2 = Convert.ToDouble(array[2]);
			if (num > num2)
			{
				m_MQTTService.Publish("Openvino/Facedetection", new
				{
					Face = "Male"
				}, retain: false);
			}
			else
			{
				m_MQTTService.Publish("Openvino/Facedetection", new
				{
					Face = "Female"
				}, retain: false);
			}
		}
	}
}
