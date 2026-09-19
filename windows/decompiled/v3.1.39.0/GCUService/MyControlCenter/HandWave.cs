using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Forms;

namespace MyControlCenter;

internal class HandWave
{
	public const int MOUSEEVENTF_LEFTDOWN = 2;

	public const int MOUSEEVENTF_LEFTUP = 4;

	private string Size = SystemInformation.PrimaryMonitorSize.ToString();

	private int Width = SystemInformation.PrimaryMonitorSize.Width;

	private int Height = SystemInformation.PrimaryMonitorSize.Height;

	private string Path = AppDomain.CurrentDomain.BaseDirectory + "human_pose_estimation.bat";

	private OpenVinoService openVinoService = OpenVinoService.Instance;

	private MqttClientCtrl m_MQTTService = MqttClientCtrl.Instance;

	private const string Topic = "Openvino/HandWave";

	private object _handLock = new object();

	private List<Point> WaveShiftList = new List<Point>();

	private double moveX;

	private double moveY;

	[DllImport("user32.dll")]
	private static extern bool SetCursorPos(int X, int Y);

	[DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
	private static extern void mouse_event(int dwFlags, int dx, int dy, int cButtons, int dwExtraInfo);

	public HandWave()
	{
		openVinoService.Init(Path);
		openVinoService.Start();
		OpenVinoService obj = openVinoService;
		obj.OutputDataReceived = (DataReceivedEventHandler)Delegate.Combine(obj.OutputDataReceived, new DataReceivedEventHandler(Process_OutputDataReceived));
	}

	public void Stop()
	{
		OpenVinoService obj = openVinoService;
		obj.OutputDataReceived = (DataReceivedEventHandler)Delegate.Remove(obj.OutputDataReceived, new DataReceivedEventHandler(Process_OutputDataReceived));
		openVinoService.Stop();
	}

	private void Process_OutputDataReceived(object sender, DataReceivedEventArgs e)
	{
		lock (_handLock)
		{
			e.Data.Split(',');
			if (e.Data.Contains("left_hand"))
			{
				double num = Convert.ToDouble(e.Data.ToString().Split(',').Skip(1)
					.First());
				if (num < 100.0 && num > 80.0)
				{
					mouse_event(6, 0, 0, 0, 0);
				}
			}
			else if (e.Data.Contains("right_cordination"))
			{
				string[] array = e.Data.ToString().Split(',');
				int num2 = Convert.ToInt32(Convert.ToDouble(array[1]));
				int num3 = Convert.ToInt32(Convert.ToDouble(array[2]));
				new Point(num2, num3);
				if (num2 < 320 && num3 > 240)
				{
					double num4 = 0.0;
					num4 = ((num2 >= 160) ? ((double)(Convert.ToInt32(Width) - Width / 320 * num2 + 70)) : ((double)(Convert.ToInt32(Width) - Width / 320 * num2 - 70)));
					double num5 = 0.0;
					num5 = ((num2 <= 120) ? ((double)(Height * (num3 - 240) / 120 + 75)) : ((double)(Height * (num3 - 240) / 120 - 75)));
					if (num4 > (double)Width)
					{
						num4 = Width;
					}
					else if (num4 < 0.0)
					{
						num4 = 0.0;
					}
					if (num5 > (double)Height)
					{
						num5 = Height;
					}
					else if (num5 < 0.0)
					{
						num5 = 0.0;
					}
					SetCursorPos(Convert.ToInt32(num4), Convert.ToInt32(num5));
				}
			}
			else
			{
				if (!e.Data.Contains("right_hand_wave"))
				{
					return;
				}
				string[] array2 = e.Data.ToString().Split(',');
				int num6 = Convert.ToInt32(Convert.ToDouble(array2[1]));
				int num7 = Convert.ToInt32(Convert.ToDouble(array2[2]));
				Point item = new Point(num6, num7);
				WaveShiftList.Add(item);
				if (WaveShiftList.Count > 2 && WaveShiftList.Last().X < WaveShiftList.Average((Point n) => n.X))
				{
					double num8 = WaveShiftList.Max((Point n) => n.X);
					double num9 = WaveShiftList.Min((Point n) => n.X);
					double distance = num8 - num9;
					m_MQTTService.Publish("Openvino/HandWave", new
					{
						Distance = distance
					}, retain: false);
					WaveShiftList.Clear();
				}
			}
		}
	}
}
