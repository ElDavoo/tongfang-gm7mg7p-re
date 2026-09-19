using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Timers;
using GCUService.MyRgbKeyboard;
using MyControlCenter;
using Utility;
using Win32Process;

namespace GCUService.MySystem;

internal class ProcessControl
{
	private bool _ProcessControlPower;

	private object ProcessLock = new object();

	private string defaultPrcessNumber = "111111111111";

	private List<string> DefaultProcessList = new List<string> { "AdobeFX", "AutoDesk" };

	private List<ProcessInfo> ProcessList = new List<ProcessInfo>();

	private Dictionary<string, ProcessSetValue> processSetDictionary = new Dictionary<string, ProcessSetValue>();

	private MqttClientCtrl m_MQTTClient = MqttClientCtrl.Instance;

	private static readonly ProcessControl model = new ProcessControl();

	private ProcessMemoryRelease _memoryRelease = new ProcessMemoryRelease();

	private Timer _TimersTimer = new Timer();

	private int _Minutes = 5;

	private const string registryName = "ProcessControl";

	private const string _ProcessControlTopic = "ProcessControl/Status";

	public static ProcessControl Instance => model;

	private ProcessControl()
	{
		_TimersTimer = new Timer();
		_TimersTimer.Interval = _Minutes * 1000 * 60;
		_TimersTimer.AutoReset = true;
		_TimersTimer.Elapsed += _TimersTimer_Elapsed;
		if (ProcessControlSave.IsRegeditExit("ProcessControl"))
		{
			LoadRegistry();
		}
	}

	private void _TimersTimer_Elapsed(object sender, ElapsedEventArgs e)
	{
		if (!_ProcessControlPower)
		{
			return;
		}
		foreach (KeyValuePair<string, ProcessSetValue> item in processSetDictionary)
		{
			SetReleaseMem(item.Key);
		}
	}

	private async void LoadRegistry()
	{
		_ = 1;
		try
		{
			string[] array = ProcessControlSave.ProcessList();
			string[] array2 = array;
			foreach (string p in array2)
			{
				AddProcessToList(p, await ProcessControlSave.ReadAsync<ProcessSetValue>("ProcessControl", p), save: false);
			}
			string text = await ProcessControlSave.ReadAsync<string>("ProcessControl\\Time", "Mins");
			if (text != null)
			{
				_Minutes = Convert.ToInt32(text);
			}
			m_MQTTClient.PublishTopic("ProcessControl/Status", new
			{
				ProcessList = processSetDictionary,
				Time = _Minutes
			}, MqttQualityOfServiceLevel.ExactlyOnce);
		}
		catch (Exception ex)
		{
			LogCtrl.Write("Process control error " + ex.ToString());
		}
	}

	private void ProcessTerminated(object sender, EventArgs e)
	{
	}

	private void ProcessStarted(object sender, EventArgs e)
	{
		ProcessInfo processInfo = sender as ProcessInfo;
		if (_ProcessControlPower)
		{
			SetProcessCPUUsage(processInfo._appName, processSetDictionary[processInfo._appName].ProcessorAffinity);
			SetProcessPriority(processInfo._appName, processSetDictionary[processInfo._appName].priority);
			if (processSetDictionary[processInfo._appName].ReleaseMemorySwitch)
			{
				SetReleaseMem(processInfo._appName);
			}
		}
		else
		{
			SetProcessCPUUsage(processInfo._appName, defaultPrcessNumber);
			SetProcessPriority(processInfo._appName, ProcessPriorityClass.Normal);
		}
	}

	public void AddProcessToList(string processName, ProcessSetValue processvalue, bool save = true)
	{
		lock (ProcessLock)
		{
			ProcessInfo processInfo = new ProcessInfo(processName);
			if (processInfo._appName != null && !processSetDictionary.ContainsKey(processInfo._appName))
			{
				processInfo.Started = (ProcessInfo.StartedEventHandler)Delegate.Combine(processInfo.Started, new ProcessInfo.StartedEventHandler(ProcessStarted));
				processInfo.Terminated = (ProcessInfo.TerminatedEventHandler)Delegate.Combine(processInfo.Terminated, new ProcessInfo.TerminatedEventHandler(ProcessTerminated));
				ProcessSetValue processSetValue = new ProcessSetValue();
				if (processvalue == null)
				{
					processSetValue.ProcessorAffinity = defaultPrcessNumber;
					processSetValue.priority = ProcessPriorityClass.Normal;
					processSetValue.ReleaseMemorySwitch = false;
					processSetDictionary.Add(processInfo._appName, processSetValue);
				}
				else
				{
					processSetValue = processvalue;
					processSetDictionary.Add(processInfo._appName, processSetValue);
				}
				if (save)
				{
					ProcessControlSave.SaveAsync("ProcessControl", processInfo._appName, processSetValue);
				}
				ProcessList.Add(processInfo);
			}
			else if (processInfo._appName != null && processSetDictionary != null && processSetDictionary.ContainsKey(processInfo._appName))
			{
				processSetDictionary[processInfo._appName] = processvalue;
				if (save)
				{
					ProcessControlSave.SaveAsync("ProcessControl", processInfo._appName, processvalue);
				}
			}
		}
	}

	public void EnableProcessing()
	{
		try
		{
			_ProcessControlPower = true;
			_TimersTimer.Start();
			SetEnableValue();
		}
		catch (Exception)
		{
		}
	}

	public void DisableProcessing()
	{
		try
		{
			_ProcessControlPower = false;
			_TimersTimer.Stop();
			SetDisableValue();
		}
		catch (Exception)
		{
		}
	}

	private void SetEnableValue()
	{
		lock (ProcessLock)
		{
			foreach (KeyValuePair<string, ProcessSetValue> item in processSetDictionary)
			{
				SetProcessCPUUsage(item.Key, item.Value.ProcessorAffinity);
				SetProcessPriority(item.Key, item.Value.priority);
				if (item.Value.ReleaseMemorySwitch)
				{
					SetReleaseMem(item.Key);
				}
			}
		}
	}

	private void SetDisableValue()
	{
		lock (ProcessLock)
		{
			foreach (KeyValuePair<string, ProcessSetValue> item in processSetDictionary)
			{
				SetProcessCPUUsage(item.Key, defaultPrcessNumber);
				SetProcessPriority(item.Key, ProcessPriorityClass.Normal);
			}
		}
	}

	internal async void Receive(byte[] message)
	{
		dynamic val = await Json.ToObjectAsync<object>(Encoding.UTF8.GetString(message));
		string process = val["Process"];
		switch (val["Action"])
		{
		case "Del":
			lock (ProcessLock)
			{
				string findProcess = processSetDictionary.Keys.SingleOrDefault((string n) => n == process);
				if (findProcess != null)
				{
					ProcessInfo processInfo = ProcessList.SingleOrDefault((ProcessInfo n) => n._appName.Equals(findProcess));
					if (processInfo != null)
					{
						ProcessList.Remove(processInfo);
					}
					processSetDictionary.Remove(findProcess);
					ProcessControlSave.DelRegistry("ProcessControl", findProcess);
				}
				break;
			}
		case "Add":
		{
			ProcessSetValue processSetValue = new ProcessSetValue();
			string processorAffinity = Convert.ToString(val["ProcessorAffinity"]);
			string text2 = val["priority"];
			bool releaseMemorySwitch = false;
			List<ProcessPriorityClass> list = EnumHelper.ToList<ProcessPriorityClass>();
			ProcessPriorityClass priority = ProcessPriorityClass.RealTime;
			foreach (ProcessPriorityClass item in list)
			{
				if (item.ToString() == text2)
				{
					priority = item;
				}
			}
			if (val["ReleaseMemorySwitch"] != null)
			{
				releaseMemorySwitch = Convert.ToBoolean(val["ReleaseMemorySwitch"]);
			}
			if (val["FullPath"] != null)
			{
				processSetValue.FullPath = Convert.ToString(val["FullPath"]);
			}
			processSetValue.ProcessorAffinity = processorAffinity;
			processSetValue.priority = priority;
			processSetValue.ReleaseMemorySwitch = releaseMemorySwitch;
			AddProcessToList(process, processSetValue);
			if (_ProcessControlPower)
			{
				SetEnableValue();
			}
			else
			{
				SetDisableValue();
			}
			break;
		}
		case "Query":
			m_MQTTClient.PublishTopic("ProcessControl/Status", new
			{
				ProcessList = processSetDictionary,
				Time = _Minutes
			}, MqttQualityOfServiceLevel.ExactlyOnce);
			break;
		case "ReleaseMem":
			SetReleaseMem(process);
			break;
		case "SetTime":
		{
			string text = val["Mins"];
			if (text != "")
			{
				SetKeyboardCloseTime(Convert.ToInt32(text));
				ProcessControlSave.SaveAsync("ProcessControl\\Time", "Mins", text);
			}
			else
			{
				SetKeyboardCloseTime(Convert.ToInt32(15));
				ProcessControlSave.SaveAsync("ProcessControl\\Time", "Mins", "15");
			}
			break;
		}
		case "OnButtonClear":
			SetOneButtonClear();
			break;
		}
	}

	private void SetOneButtonClear()
	{
		new OneBtnClear().systemCleanProcess();
	}

	public void SetKeyboardCloseTime(int mins)
	{
		try
		{
			int result = int.MaxValue;
			int.TryParse(mins.ToString(), out result);
			if (result != int.MaxValue)
			{
				_Minutes = mins;
			}
			if (_Minutes != 0)
			{
				_TimersTimer.Interval = _Minutes * 1000 * 60;
			}
			_TimersTimer.Start();
		}
		catch (Exception)
		{
			_TimersTimer.Interval = double.MaxValue;
			_TimersTimer.Stop();
		}
	}

	private void SetReleaseMem(string appName)
	{
		Process[] processesByName = Process.GetProcessesByName(appName.Replace(".exe", ""));
		foreach (Process process in processesByName)
		{
			_memoryRelease.Release(process);
		}
	}

	private void SetProcessGPU(string appName, string fullPath, int gpuLevel)
	{
	}

	private void DelProcessGPU(string appName)
	{
	}

	private void SetProcessCPUUsage(string appName, string cpuLocation)
	{
		try
		{
			if (appName == null || cpuLocation == null)
			{
				return;
			}
			Process[] processesByName = Process.GetProcessesByName(appName.Replace(".exe", ""));
			if (cpuLocation.Length < 16)
			{
				string text = "";
				for (int i = 0; i < 16 - cpuLocation.Length; i++)
				{
					text += "0";
				}
				cpuLocation = text + cpuLocation;
			}
			string s = Convert.ToInt32(cpuLocation, 2).ToString("X");
			Process[] array = processesByName;
			foreach (Process obj in array)
			{
				int num = int.Parse(s, NumberStyles.HexNumber);
				obj.ProcessorAffinity = (IntPtr)num;
			}
		}
		catch (Exception ex)
		{
			LogCtrl.Write("ProcesccControl " + ex.ToString());
		}
	}

	private void SetProcessPriority(string appName, ProcessPriorityClass priority)
	{
		Process[] processesByName = Process.GetProcessesByName(appName.Replace(".exe", ""));
		for (int i = 0; i < processesByName.Length; i++)
		{
			processesByName[i].PriorityClass = priority;
		}
	}
}
