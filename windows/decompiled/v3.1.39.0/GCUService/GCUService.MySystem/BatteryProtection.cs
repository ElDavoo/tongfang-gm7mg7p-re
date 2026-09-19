using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
using System.Timers;
using System.Windows;
using System.Windows.Forms;
using System.Windows.Threading;
using GCUService.MySystem.Battry;
using Microsoft.Win32;
using MyControlCenter;
using MyECIO;
using Utility;

namespace GCUService.MySystem;

internal class BatteryProtection
{
	private static readonly BatteryProtection BatteryProtectionmodel = new BatteryProtection();

	public MqttClientCtrl m_MQTTClient = MqttClientCtrl.Instance;

	private BatteryPercentManger battry = new BatteryPercentManger();

	private System.Timers.Timer _Timer = new System.Timers.Timer();

	private DateTime ApInstalledTime;

	private DateTime OpenOSTime;

	private DateTime OpenHealthTime;

	private int PowerProtectionMin = 7;

	private int PowerProtectionMax = 100;

	private int PowerCorrectionMin = 7;

	private int PowerCorrectionMax = 100;

	private bool _ProtecionSwitch;

	private bool _CorretionSwitch;

	private bool _NotificationSwitch = true;

	private string _FinishDateTime = "0";

	private uint _HealthProtectionStauts;

	private uint _BatteryPowerStatus;

	private bool _BatteryProctionSupport;

	private STAGE_STATUS _ProtectionSTAGE1;

	private STAGE_STATUS _ProtectionSTAGE2;

	private STAGE_STATUS _CorrenctionSTAGE1;

	private STAGE_STATUS _CorrenctionSTAGE2;

	private STAGE_STATUS _CorrenctionSTAGE3;

	private const string m_sRegistryPath = "\\OEM\\GamingCenter2\\BatteryProtection";

	public static List<NotificationWindow> _dialogs = new List<NotificationWindow>();

	private int i;

	private string m_sLang = "en-us";

	private string m_sRegPath = "\\OEM\\GamingCenter2";

	private Dispatcher mainDispatcher;

	public static BatteryProtection Instance => BatteryProtectionmodel;

	private string FinishDateTime
	{
		get
		{
			return _FinishDateTime;
		}
		set
		{
			if (value != _FinishDateTime)
			{
				_FinishDateTime = value;
				SaveToRegistryString("FinishDateTime", value);
			}
		}
	}

	public bool NotificationSwitch
	{
		get
		{
			return _NotificationSwitch;
		}
		set
		{
			if (value != _NotificationSwitch)
			{
				_NotificationSwitch = value;
				SaveToRegistry("NotificationSwitch", value);
			}
		}
	}

	public bool CorretionSwitch
	{
		get
		{
			return _CorretionSwitch;
		}
		set
		{
			if (value != _CorretionSwitch)
			{
				_CorretionSwitch = value;
				SaveToRegistry("CorretionSwitch", value);
			}
		}
	}

	public bool ProtectionSwitch
	{
		get
		{
			return _ProtecionSwitch;
		}
		set
		{
			if (value != _ProtecionSwitch)
			{
				_ProtecionSwitch = value;
				SaveToRegistry("ProtectionSwitch", value);
			}
		}
	}

	public uint HealthProtectionStauts
	{
		get
		{
			return _HealthProtectionStauts;
		}
		set
		{
			if (value != _HealthProtectionStauts)
			{
				_HealthProtectionStauts = value;
				SaveToRegistry("HealthProtectionStauts", value);
			}
		}
	}

	public uint BatteryPowerStatus
	{
		get
		{
			return _BatteryPowerStatus;
		}
		set
		{
			if (value != _BatteryPowerStatus)
			{
				_BatteryPowerStatus = value;
				SaveToRegistry("BatteryPowerStatus", value);
			}
		}
	}

	public bool BatteryProctionSupport
	{
		get
		{
			return _BatteryProctionSupport;
		}
		set
		{
			if (value != _BatteryProctionSupport)
			{
				_BatteryProctionSupport = value;
				SaveToRegistry("_BatteryProctionSupport", value);
			}
		}
	}

	public STAGE_STATUS ProtectionSTAGE1
	{
		get
		{
			return _ProtectionSTAGE1;
		}
		set
		{
			if (value != _ProtectionSTAGE1)
			{
				_ProtectionSTAGE1 = value;
				SaveToRegistry("ProtectionSTAGE1", value);
			}
		}
	}

	public STAGE_STATUS ProtectionSTAGE2
	{
		get
		{
			return _ProtectionSTAGE2;
		}
		set
		{
			if (value != _ProtectionSTAGE2)
			{
				_ProtectionSTAGE2 = value;
				SaveToRegistry("ProtectionSTAGE2", value);
			}
		}
	}

	public STAGE_STATUS CorrenctionSTAGE1
	{
		get
		{
			return _CorrenctionSTAGE1;
		}
		set
		{
			if (value != _CorrenctionSTAGE1)
			{
				_CorrenctionSTAGE1 = value;
				SaveToRegistry("CorrenctionSTAGE1", value);
			}
		}
	}

	public STAGE_STATUS CorrenctionSTAGE2
	{
		get
		{
			return _CorrenctionSTAGE2;
		}
		set
		{
			if (value != _CorrenctionSTAGE2)
			{
				_CorrenctionSTAGE2 = value;
				SaveToRegistry("CorrenctionSTAGE2", value);
			}
		}
	}

	public STAGE_STATUS CorrenctionSTAGE3
	{
		get
		{
			return _CorrenctionSTAGE3;
		}
		set
		{
			if (value != _CorrenctionSTAGE3)
			{
				_CorrenctionSTAGE3 = value;
				SaveToRegistry("CorrenctionSTAGE3", value);
			}
		}
	}

	private BatteryProtection()
	{
		InitializeHealthSwitch();
		InitializePowerCorrectionStatus();
		SystemEvents.PowerModeChanged += SystemEvents_PowerModeChanged;
		battry.LifePercentChange += Battry_LifePercentChange_Auto;
		battry.LifePercentChange += Battry_LifePercentChange;
	}

	public void Resume()
	{
		setHealthProtectinStatus();
	}

	private void SystemEvents_PowerModeChanged(object sender, PowerModeChangedEventArgs e)
	{
		if (e.Mode == PowerModes.StatusChange)
		{
			if (SystemInformation.PowerStatus.PowerLineStatus.ToString().Equals("Offline"))
			{
				BatteryPowerStatus = 0u;
				var status = new
				{
					BatteryPowerStatus = BatteryPowerStatus,
					BatteryPercent = Convert.ToInt32(battry.GetCurrentBatteryLifePercent()),
					BatteryTime = Convert.ToInt32(battry.GetCurrentBatteryLifeTime())
				};
				SendToUI(status);
			}
			else if (SystemInformation.PowerStatus.PowerLineStatus.ToString().Equals("Online"))
			{
				BatteryPowerStatus = 1u;
				var status2 = new
				{
					BatteryPowerStatus = BatteryPowerStatus,
					BatteryPercent = Convert.ToInt32(battry.GetCurrentBatteryLifePercent()),
					BatteryTime = -1
				};
				SendToUI(status2);
			}
		}
	}

	private void InitializePowerCorrectionStatus()
	{
		SetupPara.nBatteryCalibration = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "BatteryCalibration", 0);
		if (SetupPara.nBatteryCalibration == 0)
		{
			Reset();
			NotificationSwitch = false;
			return;
		}
		if (BatteryProctionSupport)
		{
			Reset();
			NotificationSwitch = false;
			return;
		}
		NotificationSwitch = true;
		CorretionSwitch = LoadSwitchFromRegistry("CorretionSwitch");
		ProtectionSTAGE1 = LoadStatusFromRegistry("ProtectionSTAGE1");
		ProtectionSTAGE2 = LoadStatusFromRegistry("ProtectionSTAGE2");
		CorrenctionSTAGE1 = LoadStatusFromRegistry("CorrenctionSTAGE1");
		CorrenctionSTAGE2 = LoadStatusFromRegistry("CorrenctionSTAGE2");
		CorrenctionSTAGE3 = LoadStatusFromRegistry("CorrenctionSTAGE3");
		FinishDateTime = LoadStatusFromRegistryString("FinishDateTime");
		if (CorretionSwitch)
		{
			AutoCorrection(battry.GetCurrentBatteryLifePercent());
		}
	}

	private void setHealthProtectinStatus()
	{
		HealthProtectionStauts = (uint)LoadStatusFromRegistry("HealthProtectionStauts");
		if (HealthProtectionStauts == 0)
		{
			SetProtectionHigh();
		}
		else if (HealthProtectionStauts == 1)
		{
			SetProtectionMiddle();
		}
		else if (HealthProtectionStauts == 2)
		{
			SetProtectionLow();
		}
		else
		{
			LogCtrl.Write("Set battery protection fail");
		}
	}

	private void InitializeHealthSwitch()
	{
		try
		{
			BatteryPowerStatus = (uint)LoadStatusFromRegistry("BatteryPowerStatus");
			HealthProtectionStauts = (uint)LoadStatusFromRegistry("HealthProtectionStauts");
			byte Data = 0;
			MyEcCtrl.Instance.Read(GetType().Name, 1934, ref Data);
			BitArray bitArray = new BitArray(new byte[1] { Data });
			BatteryProctionSupport = bitArray[3];
			setHealthProtectinStatus();
		}
		catch
		{
		}
	}

	public void SetHealthSwitch(bool enable)
	{
	}

	public void SetProtectionHigh()
	{
		byte Data = 0;
		MyEcCtrl.Instance.Read(GetType().Name, 1958, ref Data);
		BitArray bitArray = new BitArray(new byte[1] { Data });
		bitArray[4] = false;
		bitArray[5] = false;
		byte data = ConvertToByte(bitArray);
		MyEcCtrl.Instance.Write(GetType().Name, 1958, data);
		HealthProtectionStauts = Convert.ToUInt32(Protection_Status.PERFORMANCEDMODE);
	}

	public void SetProtectionMiddle()
	{
		byte Data = 0;
		MyEcCtrl.Instance.Read(GetType().Name, 1958, ref Data);
		BitArray bitArray = new BitArray(new byte[1] { Data });
		bitArray[4] = true;
		bitArray[5] = false;
		byte data = ConvertToByte(bitArray);
		MyEcCtrl.Instance.Write(GetType().Name, 1958, data);
		HealthProtectionStauts = Convert.ToUInt32(Protection_Status.BALANCEDMODE);
	}

	public void SetProtectionLow()
	{
		byte Data = 0;
		MyEcCtrl.Instance.Read(GetType().Name, 1958, ref Data);
		BitArray bitArray = new BitArray(new byte[1] { Data });
		bitArray[4] = false;
		bitArray[5] = true;
		byte data = ConvertToByte(bitArray);
		MyEcCtrl.Instance.Write(GetType().Name, 1958, data);
		HealthProtectionStauts = Convert.ToUInt32(Protection_Status.HEALTHYMODE);
	}

	private byte ConvertToByte(BitArray bits)
	{
		_ = bits.Count;
		_ = 8;
		byte[] array = new byte[1];
		bits.CopyTo(array, 0);
		return array[0];
	}

	private void Battry_LifePercentChange_Auto(object sender, EventArgs e)
	{
		try
		{
			AutoProtection(sender);
			AutoCorrection(sender);
		}
		catch (Exception ex)
		{
			LogCtrl.Write("Battry info " + ex.ToString());
		}
	}

	private void Battry_LifePercentChange(object sender, EventArgs e)
	{
		try
		{
			int result = 65535;
			int result2 = 0;
			int.TryParse(sender.ToString(), out result);
			int.TryParse(battry.GetCurrentBatteryLifeTime(), out result2);
			var status = new
			{
				BatteryPercent = result,
				BatteryTime = result2
			};
			SendToUI(status);
		}
		catch (Exception ex)
		{
			LogCtrl.Write("Battry percent " + ex.ToString());
		}
	}

	private void AutoProtection(object sender)
	{
		if (ProtectionSwitch)
		{
			return;
		}
		PowerStatus powerStatus = SystemInformation.PowerStatus;
		if (Convert.ToInt32(sender) <= PowerProtectionMin)
		{
			ProtectionSTAGE1 = STAGE_STATUS.Completed;
			ProtectionSTAGE2 = STAGE_STATUS.Continue;
			var status = new
			{
				HealthProtectionStauts = HealthProtectionStauts,
				BatteryPercent = Convert.ToInt32(sender),
				BatteryTime = Convert.ToInt32(battry.GetCurrentBatteryLifeTime()),
				ProtectionSTAGE1 = ProtectionSTAGE1,
				ProtectionSTAGE2 = ProtectionSTAGE2
			};
			SendToUI(status);
			return;
		}
		if (ProtectionSTAGE1 == STAGE_STATUS.Completed && powerStatus.PowerLineStatus == System.Windows.Forms.PowerLineStatus.Online && Convert.ToInt32(sender).Equals(PowerProtectionMax))
		{
			ProtectionSTAGE2 = STAGE_STATUS.Completed;
			ProtectionSwitch = false;
			var status2 = new
			{
				HealthProtectionStauts = HealthProtectionStauts,
				BatteryPercent = Convert.ToInt32(sender),
				BatteryTime = Convert.ToInt32(battry.GetCurrentBatteryLifeTime()),
				ProtectionSTAGE1 = ProtectionSTAGE1,
				ProtectionSTAGE2 = ProtectionSTAGE2
			};
			SendToUI(status2);
			return;
		}
		if (ProtectionSTAGE1 == STAGE_STATUS.None)
		{
			ProtectionSTAGE1 = STAGE_STATUS.Continue;
		}
		else if (ProtectionSTAGE1 == STAGE_STATUS.Completed && ProtectionSTAGE2 == STAGE_STATUS.None)
		{
			ProtectionSTAGE2 = STAGE_STATUS.Continue;
		}
		var status3 = new
		{
			HealthProtectionStauts = HealthProtectionStauts,
			BatteryPercent = Convert.ToInt32(sender),
			BatteryTime = Convert.ToInt32(battry.GetCurrentBatteryLifeTime()),
			ProtectionSTAGE1 = ProtectionSTAGE1,
			ProtectionSTAGE2 = ProtectionSTAGE2
		};
		SendToUI(status3);
	}

	private async void AutoCorrection(object sender)
	{
		if (!CorretionSwitch)
		{
			return;
		}
		PowerStatus powerStatus = SystemInformation.PowerStatus;
		if (powerStatus.PowerLineStatus == System.Windows.Forms.PowerLineStatus.Online && CorrenctionSTAGE1 != STAGE_STATUS.Completed && Convert.ToInt32(sender).Equals(PowerCorrectionMax))
		{
			CorrenctionSTAGE1 = STAGE_STATUS.Completed;
			CorrenctionSTAGE2 = STAGE_STATUS.Continue;
			if (Convert.ToInt32(sender).Equals(PowerCorrectionMax))
			{
				NotificationShow("step2");
			}
			var status = new
			{
				HealthProtectionStauts = HealthProtectionStauts,
				BatteryPercent = Convert.ToInt32(sender),
				BatteryTime = Convert.ToInt32(battry.GetCurrentBatteryLifeTime()),
				CorrenctionSTAGE1 = CorrenctionSTAGE1,
				CorrenctionSTAGE2 = CorrenctionSTAGE2,
				CorrenctionSTAGE3 = CorrenctionSTAGE3,
				FinishDateTime = FinishDateTime
			};
			SendToUI(status);
			return;
		}
		if (powerStatus.PowerLineStatus == System.Windows.Forms.PowerLineStatus.Offline && CorrenctionSTAGE1 == STAGE_STATUS.Completed && CorrenctionSTAGE2 != STAGE_STATUS.Completed && Convert.ToInt32(sender) <= PowerCorrectionMin)
		{
			CorrenctionSTAGE2 = STAGE_STATUS.Completed;
			CorrenctionSTAGE3 = STAGE_STATUS.Continue;
			if (Convert.ToInt32(sender).Equals(PowerCorrectionMin))
			{
				NotificationShow("step3");
			}
			var status2 = new
			{
				HealthProtectionStauts = HealthProtectionStauts,
				BatteryPercent = Convert.ToInt32(sender),
				BatteryTime = Convert.ToInt32(battry.GetCurrentBatteryLifeTime()),
				CorrenctionSTAGE1 = CorrenctionSTAGE1,
				CorrenctionSTAGE2 = CorrenctionSTAGE2,
				CorrenctionSTAGE3 = CorrenctionSTAGE3,
				FinishDateTime = FinishDateTime
			};
			SendToUI(status2);
			return;
		}
		if (powerStatus.PowerLineStatus == System.Windows.Forms.PowerLineStatus.Online && CorrenctionSTAGE1 == STAGE_STATUS.Completed && CorrenctionSTAGE2 == STAGE_STATUS.Completed && CorrenctionSTAGE3 != STAGE_STATUS.Completed && Convert.ToInt32(sender).Equals(PowerCorrectionMax))
		{
			CorrenctionSTAGE3 = STAGE_STATUS.Completed;
			CorretionSwitch = false;
			if (Convert.ToInt32(sender).Equals(PowerCorrectionMax))
			{
				FinishDateTime = DateTime.Now.ToString("yyyyMMddHHmmss");
				NotificationShow("finish");
			}
			var status3 = new
			{
				HealthProtectionStauts = HealthProtectionStauts,
				BatteryPercent = Convert.ToInt32(sender),
				BatteryTime = Convert.ToInt32(battry.GetCurrentBatteryLifeTime()),
				CorrenctionSTAGE1 = CorrenctionSTAGE1,
				CorrenctionSTAGE2 = CorrenctionSTAGE2,
				CorrenctionSTAGE3 = CorrenctionSTAGE3,
				FinishDateTime = FinishDateTime
			};
			SendToUI(status3);
			return;
		}
		if (CorrenctionSTAGE1 == STAGE_STATUS.None)
		{
			CorrenctionSTAGE1 = STAGE_STATUS.Continue;
		}
		else if (CorrenctionSTAGE1 == STAGE_STATUS.Completed && CorrenctionSTAGE2 == STAGE_STATUS.None)
		{
			CorrenctionSTAGE2 = STAGE_STATUS.Continue;
		}
		else if (CorrenctionSTAGE1 == STAGE_STATUS.Completed && CorrenctionSTAGE2 == STAGE_STATUS.Completed && CorrenctionSTAGE3 == STAGE_STATUS.None)
		{
			CorrenctionSTAGE3 = STAGE_STATUS.Continue;
		}
		var status4 = new
		{
			HealthProtectionStauts = HealthProtectionStauts,
			BatteryPercent = Convert.ToInt32(sender),
			BatteryTime = Convert.ToInt32(battry.GetCurrentBatteryLifeTime()),
			CorrenctionSTAGE1 = CorrenctionSTAGE1,
			CorrenctionSTAGE2 = CorrenctionSTAGE2,
			CorrenctionSTAGE3 = CorrenctionSTAGE3,
			FinishDateTime = FinishDateTime
		};
		SendToUI(status4);
	}

	private void Reset()
	{
		CorrenctionSTAGE1 = STAGE_STATUS.None;
		CorrenctionSTAGE2 = STAGE_STATUS.None;
		CorrenctionSTAGE3 = STAGE_STATUS.None;
		CorretionSwitch = false;
		ProtectionSTAGE1 = STAGE_STATUS.None;
		ProtectionSTAGE2 = STAGE_STATUS.None;
		ProtectionSwitch = false;
		OpenHealthTime = DateTime.Now;
		var status = new { HealthProtectionStauts, CorrenctionSTAGE1, CorrenctionSTAGE2, CorrenctionSTAGE3, ProtectionSTAGE1, ProtectionSTAGE2 };
		SendToUI(status);
	}

	private bool LoadSwitchFromRegistry(string Name)
	{
		return Convert.ToBoolean((int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\BatteryProtection", Name, 1));
	}

	private STAGE_STATUS LoadStatusFromRegistry(string StageName)
	{
		try
		{
			return (STAGE_STATUS)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\BatteryProtection", StageName, STAGE_STATUS.None);
		}
		catch
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\BatteryProtection", StageName, STAGE_STATUS.None, RegistryValueKind.DWord);
		}
		return STAGE_STATUS.None;
	}

	private string LoadStatusFromRegistryString(string StageName)
	{
		try
		{
			return (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\BatteryProtection", StageName, STAGE_STATUS.None);
		}
		catch
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\BatteryProtection", StageName, "0", RegistryValueKind.String);
		}
		return "0";
	}

	private void SaveToRegistryString(string StageName, object stage)
	{
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\BatteryProtection", StageName, stage, RegistryValueKind.String);
	}

	private void SaveToRegistry(string StageName, object stage)
	{
		RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, "\\OEM\\GamingCenter2\\BatteryProtection", StageName, stage, RegistryValueKind.DWord);
	}

	private void SendToUI(dynamic status)
	{
		m_MQTTClient.Publish("System/BatteryProtection", status, false);
	}

	private void _Timer_Elapsed(object sender, ElapsedEventArgs e)
	{
	}

	private void CorrectionTime(int days)
	{
		_ = (DateTime.Now - ApInstalledTime).Days;
	}

	public void AllPowerStatus()
	{
		PropertyInfo[] properties = typeof(PowerStatus).GetProperties();
		for (int i = 0; i < properties.Length; i++)
		{
		}
	}

	private double GetTopFrom()
	{
		double topFrom = SystemParameters.WorkArea.Bottom - 10.0;
		bool flag = _dialogs.Any((NotificationWindow o) => o.TopFrom == topFrom);
		while (flag)
		{
			topFrom -= 150.0;
			flag = _dialogs.Any((NotificationWindow o) => o.TopFrom == topFrom);
		}
		if (topFrom <= 0.0)
		{
			topFrom = SystemParameters.WorkArea.Bottom - 10.0;
		}
		return topFrom;
	}

	private void Dialog_Closed(object sender, EventArgs e)
	{
		NotificationWindow item = sender as NotificationWindow;
		_dialogs.Remove(item);
	}

	internal async void Receive(byte[] message)
	{
		dynamic tmp2 = await Json.ToObjectAsync<object>(Encoding.UTF8.GetString(message));
		if (tmp2["Action"] != null)
		{
			string text = ((string)tmp2["Action"]).ToUpperInvariant();
			if (text == Protection_Status.PERFORMANCEDMODE.ToString())
			{
				SetProtectionHigh();
			}
			else if (text == Protection_Status.BALANCEDMODE.ToString())
			{
				SetProtectionMiddle();
			}
			else if (text == Protection_Status.HEALTHYMODE.ToString())
			{
				SetProtectionLow();
			}
			if (text.Contains("NOTIFICATIONSWITCH"))
			{
				NotificationSwitch = (text.Contains("_ON") ? true : false);
			}
		}
		if (tmp2["Report"] != null)
		{
			string obj = tmp2["Report"];
			if (SystemInformation.PowerStatus.PowerLineStatus.ToString().Equals("Online"))
			{
				BatteryPowerStatus = 1u;
			}
			if (obj.Contains("GET"))
			{
				await Task.Run(delegate
				{
					SendToUI(new
					{
						BatteryPowerStatus = BatteryPowerStatus,
						BatteryProctionSupport = BatteryProctionSupport,
						BatteryPercent = Convert.ToInt32(battry.GetCurrentBatteryLifePercent()),
						BatteryTime = Convert.ToInt32(battry.GetCurrentBatteryLifeTime()),
						HealthProtectionStauts = HealthProtectionStauts,
						CorrenctionSTAGE1 = CorrenctionSTAGE1,
						CorrenctionSTAGE2 = CorrenctionSTAGE2,
						CorrenctionSTAGE3 = CorrenctionSTAGE3,
						ProtectionSTAGE1 = ProtectionSTAGE1,
						ProtectionSTAGE2 = ProtectionSTAGE2,
						NotificationSwitch = NotificationSwitch,
						FinishDateTime = FinishDateTime
					});
				});
			}
		}
		if ((tmp2["Correction"] != null) && ((string)tmp2["Correction"]).ToLowerInvariant().Contains("start"))
		{
			Reset();
			NotificationShow("step1");
			CorretionSwitch = true;
			AutoCorrection(battry.GetCurrentBatteryLifePercent());
		}
		if ((tmp2["Protection"] != null) && ((string)tmp2["Protection"]).ToLowerInvariant().Contains("start"))
		{
			Reset();
			ProtectionSwitch = true;
			AutoProtection(battry.GetCurrentBatteryLifePercent());
		}
	}

	private async void NotificationShow(string stageStatus)
	{
		if (!NotificationSwitch)
		{
			return;
		}
		try
		{
			ResourceDictionary stringDictionary = SetResourceDictionary();
			await (mainDispatcher?.BeginInvoke((Action)delegate
			{
				string titleString = Convert.ToString(stringDictionary["strNotificationTitle"]);
				string messageString = Convert.ToString(stringDictionary["strNotificationMessage"]);
				string stepString = Convert.ToString(stringDictionary["strNotificationStep1"]);
				string stepString2 = Convert.ToString(stringDictionary["strNotificationStep2"]);
				string stepString3 = Convert.ToString(stringDictionary["strNotificationStep3"]);
				string messageString2 = Convert.ToString(stringDictionary["strNotificationFinish"]);
				string stepInfoString = Convert.ToString(stringDictionary["strNotificationStep1Info"]);
				string stepInfoString2 = Convert.ToString(stringDictionary["strNotificationStep2Info"]);
				string stepInfoString3 = Convert.ToString(stringDictionary["strNotificationStep3Info"]);
				NotificationWindow notificationWindow = null;
				switch (stageStatus)
				{
				case "step1":
					notificationWindow = new NotificationWindow(titleString, messageString, stepString, stepInfoString, "pack://application:,,,/Assets/battery-step1.png");
					break;
				case "step2":
					notificationWindow = new NotificationWindow(titleString, messageString, stepString2, stepInfoString2, "pack://application:,,,/Assets/battery-step2.png");
					break;
				case "step3":
					notificationWindow = new NotificationWindow(titleString, messageString, stepString3, stepInfoString3, "pack://application:,,,/Assets/battery-step3.png");
					break;
				case "finish":
					notificationWindow = new NotificationWindow(titleString, messageString2, "", "", "pack://application:,,,/Assets/ico-calibration-done.png");
					break;
				}
				if (notificationWindow != null)
				{
					notificationWindow.Closed += Dialog_Closed;
					notificationWindow.TopFrom = GetTopFrom();
					_dialogs.Add(notificationWindow);
					notificationWindow.Show();
				}
			}, DispatcherPriority.Background));
		}
		catch (Exception)
		{
		}
	}

	private ResourceDictionary SetResourceDictionary()
	{
		try
		{
			m_sLang = (string)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegPath, "Language", "en-us");
		}
		catch
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegPath, "Language", m_sLang, RegistryValueKind.String);
		}
		ResourceDictionary resourceDictionary = new ResourceDictionary();
		string text = "..\\MySystem\\Battry\\Language";
		switch (m_sLang)
		{
		case "en-us":
			resourceDictionary.Source = new Uri(text + "\\en-US.xaml", UriKind.Relative);
			break;
		case "zh-cn":
			resourceDictionary.Source = new Uri(text + "\\zh-CN.xaml", UriKind.Relative);
			break;
		case "tr-tr":
			resourceDictionary.Source = new Uri(text + "\\tr-Tr.xaml", UriKind.Relative);
			break;
		case "zh-tw":
			resourceDictionary.Source = new Uri(text + "\\zh-TW.xaml", UriKind.Relative);
			break;
		case "de-de":
			resourceDictionary.Source = new Uri(text + "\\de-DE.xaml", UriKind.Relative);
			break;
		case "hu-hu":
			resourceDictionary.Source = new Uri(text + "\\hu-HU.xaml", UriKind.Relative);
			break;
		case "ko-kr":
			resourceDictionary.Source = new Uri(text + "\\ko-KR.xaml", UriKind.Relative);
			break;
		case "ru-ru":
			resourceDictionary.Source = new Uri(text + "\\ru-RU.xaml", UriKind.Relative);
			break;
		case "ja-jp":
			resourceDictionary.Source = new Uri(text + "\\ja-JP.xaml", UriKind.Relative);
			break;
		case "pl-pl":
			resourceDictionary.Source = new Uri(text + "\\pl-PL.xaml", UriKind.Relative);
			break;
		case "es-es":
			resourceDictionary.Source = new Uri(text + "\\es-ES.xaml", UriKind.Relative);
			break;
		case "fr-fr":
			resourceDictionary.Source = new Uri(text + "\\fr-FR.xaml", UriKind.Relative);
			break;
		case "pt-br":
			resourceDictionary.Source = new Uri(text + "\\pt-BR.xaml", UriKind.Relative);
			break;
		default:
			resourceDictionary.Source = new Uri(text + "\\en-US.xaml", UriKind.Relative);
			break;
		}
		Task<object> task = ReflashUIString(resourceDictionary);
		foreach (object key in resourceDictionary.Keys)
		{
			if (((dynamic)task.Result)?[key] != null)
			{
				resourceDictionary[key] = (object)((dynamic)task.Result)[key];
			}
		}
		return resourceDictionary;
	}

	private async Task<dynamic> ReflashUIString(ResourceDictionary dict)
	{
		string sLang = m_sLang;
		object fileResource = null;
		try
		{
			fileResource = await LoadLanguageResourceFromPath<object>(sLang, Assembly.GetExecutingAssembly());
		}
		catch (Exception ex)
		{
			LogCtrl.Write($"OSD | ReflashUIString | LoadLanguageResourceFromPath Failed {ex.ToString()}");
		}
		return fileResource;
	}

	private static async Task<T> LoadLanguageResourceFromPath<T>(string language, Assembly assembly)
	{
		string path = string.Concat(LogCtrl.GetParentDirectoryPath(System.Windows.Forms.Application.StartupPath, 2) + "\\logo", "\\Language\\", language, ".json");
		if (File.Exists(path))
		{
			return await Json.ToObjectAsync<T>(File.ReadAllText(path));
		}
		return default(T);
	}

	internal void SetDispatcher(Dispatcher dispatcher)
	{
		mainDispatcher = dispatcher;
	}
}
