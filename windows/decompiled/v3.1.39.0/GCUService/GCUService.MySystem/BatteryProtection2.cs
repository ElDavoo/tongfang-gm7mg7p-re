using System;
using System.Collections;
using System.Reflection;
using System.Text;
using System.Timers;
using System.Windows.Forms;
using Microsoft.Win32;
using MyControlCenter;
using MyECIO;
using Utility;

namespace GCUService.MySystem;

internal class BatteryProtection2
{
	private enum BatteryHealthProtection_Status
	{
		PERFORMANCEDMODE,
		BALANCEDMODE,
		HEALTHYMODE
	}

	private enum Battery_Commands
	{
		GET,
		CHARGING_UP_LIMIT,
		CHARGING_DOWN_LIMIT,
		RECOVERY,
		TYPE_C_ADAPTOR_PRIORITY_SWITCH_ON,
		TYPE_C_ADAPTOR_PRIORITY_SWITCH_OFF
	}

	private string className = "[" + MethodBase.GetCurrentMethod().DeclaringType.Name + "] ";

	private static readonly BatteryProtection2 BatteryProtectionmodel = new BatteryProtection2();

	public MqttClientCtrl m_MQTTClient = MqttClientCtrl.Instance;

	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private BatteryPercentManger battry = new BatteryPercentManger();

	private System.Timers.Timer _Timer = new System.Timers.Timer();

	private string m_sRegCurrentPath = "\\OEM\\GamingCenter2\\BatteryProtection2";

	private int m_HealthProtectionStatus;

	private int m_BatteryChargingLimit_Up_Default = 100;

	private int m_BatteryChargingLimit_Down_Default = 95;

	private int m_TypeCAdaptorPrioritySwitch;

	private bool m_TypeCAdaptorPrioritySupport;

	private int m_nCustomizeTarget = 1;

	private uint _BatteryPowerStatus;

	private int _BatteryChargingLimit_Up;

	private int _BatteryChargingLimit_Down;

	private int _BatteryLimitationMode;

	public static BatteryProtection2 Instance => BatteryProtectionmodel;

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
			}
		}
	}

	private int m_BatteryChargingLimit_Up
	{
		get
		{
			return _BatteryChargingLimit_Up;
		}
		set
		{
			if (value != _BatteryChargingLimit_Up)
			{
				_BatteryChargingLimit_Up = value;
				NvramVariable.SetFwVars("ChargeMaximumLimit", Convert.ToByte(value));
			}
		}
	}

	private int m_BatteryChargingLimit_Down
	{
		get
		{
			return _BatteryChargingLimit_Down;
		}
		set
		{
			if (value != _BatteryChargingLimit_Down)
			{
				_BatteryChargingLimit_Down = value;
				NvramVariable.SetFwVars("ChargeMinimumLimit", Convert.ToByte(value));
			}
		}
	}

	private int m_BatteryLimitationMode
	{
		get
		{
			return _BatteryLimitationMode;
		}
		set
		{
			if (value != _BatteryLimitationMode)
			{
				_BatteryLimitationMode = value;
				NvramVariable.SetFwVars("BatteryLimitation", Convert.ToByte(value));
			}
		}
	}

	private BatteryProtection2()
	{
	}

	public void EnableByService()
	{
		m_nCustomizeTarget = RegistryCtrl.GetCustomizeTarget();
		m_TypeCAdaptorPrioritySupport = EcCtrl.GetTypeCAdaptorPrioritySupport();
		LogCtrl.TraceMessage("m_TypeCAdaptorPrioritySupport: " + m_TypeCAdaptorPrioritySupport, "EnableByService", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySystem\\Battry\\BatteryProtection2.cs", 126);
		Init();
		SystemEvents.PowerModeChanged += SystemEvents_PowerModeChanged;
		battry.LifePercentChange += Battry_LifePercentChange;
	}

	public void Resume()
	{
		SetHealthProtectionStatus();
		SetTypeCAdaptorSwitch(0);
	}

	public async void Receive(byte[] message)
	{
		dynamic val = await Json.ToObjectAsync<object>(Encoding.UTF8.GetString(message));
		if (val["Action"] != null)
		{
			string text = ((string)val["Action"]).ToUpperInvariant();
			if (text == BatteryHealthProtection_Status.PERFORMANCEDMODE.ToString())
			{
				m_HealthProtectionStatus = Convert.ToInt32(BatteryHealthProtection_Status.PERFORMANCEDMODE);
				SetRegistry("HealthProtectionStatus", m_HealthProtectionStatus);
				SetHealthProtectionHigh();
			}
			else if (text == BatteryHealthProtection_Status.BALANCEDMODE.ToString())
			{
				m_HealthProtectionStatus = Convert.ToInt32(BatteryHealthProtection_Status.BALANCEDMODE);
				SetRegistry("HealthProtectionStatus", m_HealthProtectionStatus);
				SetHealthProtectionMiddle();
			}
			else if (text == BatteryHealthProtection_Status.HEALTHYMODE.ToString())
			{
				m_HealthProtectionStatus = Convert.ToInt32(BatteryHealthProtection_Status.HEALTHYMODE);
				SetRegistry("HealthProtectionStatus", m_HealthProtectionStatus);
				SetHealthProtectionLow();
			}
			else if (text == Battery_Commands.RECOVERY.ToString())
			{
				m_HealthProtectionStatus = Convert.ToInt32(BatteryHealthProtection_Status.PERFORMANCEDMODE);
				SetRegistry("HealthProtectionStatus", m_HealthProtectionStatus);
				SetHealthProtectionHigh();
				UpdateStatusToClient();
			}
			else if (text == Battery_Commands.TYPE_C_ADAPTOR_PRIORITY_SWITCH_ON.ToString())
			{
				m_TypeCAdaptorPrioritySwitch = 1;
				SetTypeCAdaptorSwitch(1);
			}
			else if (text == Battery_Commands.TYPE_C_ADAPTOR_PRIORITY_SWITCH_OFF.ToString())
			{
				m_TypeCAdaptorPrioritySwitch = 0;
				SetTypeCAdaptorSwitch(0);
			}
		}
		else if ((val["Report"] != null) && ((string)val["Report"]).ToUpperInvariant() == Battery_Commands.GET.ToString())
		{
			UpdateStatusToClient();
		}
	}

	private void Init()
	{
		try
		{
			m_HealthProtectionStatus = (int)RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, m_sRegCurrentPath, "HealthProtectionStatus", BatteryHealthProtection_Status.PERFORMANCEDMODE);
		}
		catch
		{
			m_HealthProtectionStatus = 0;
			SetRegistry("HealthProtectionStatus", m_HealthProtectionStatus);
		}
		SetHealthProtectionStatus();
		if (m_nCustomizeTarget == 11)
		{
			m_TypeCAdaptorPrioritySwitch = 1;
		}
		else
		{
			m_TypeCAdaptorPrioritySwitch = 0;
		}
		SetTypeCAdaptorSwitch(m_TypeCAdaptorPrioritySwitch);
	}

	private void LoadBatteryLimitationDefault()
	{
		if (m_BatteryChargingLimit_Up != m_BatteryChargingLimit_Up_Default || m_BatteryChargingLimit_Down != m_BatteryChargingLimit_Down_Default)
		{
			m_BatteryLimitationMode = 1;
		}
	}

	public void Uninstall()
	{
		LogCtrl.TraceMessage("---------------" + LogCtrl.GetTime() + "---------------", "Uninstall", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySystem\\Battry\\BatteryProtection2.cs", 307);
		LogCtrl.TraceMessage("Start", "Uninstall", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySystem\\Battry\\BatteryProtection2.cs", 308);
		SetHealthProtectionHigh();
		SetTypeCAdaptorSwitch(0);
	}

	public void Disable()
	{
		LogCtrl.TraceMessage("---------------" + LogCtrl.GetTime() + "---------------", "Disable", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySystem\\Battry\\BatteryProtection2.cs", 325);
		LogCtrl.TraceMessage("Start", "Disable", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySystem\\Battry\\BatteryProtection2.cs", 326);
		SetHealthProtectionHigh();
		SetTypeCAdaptorSwitch(0);
	}

	private void SetRegistry(string name, int value)
	{
		if (name == "HealthProtectionStatus")
		{
			RegistryCtrl.RegistrySoftwareKeyWrite(RegistryHive.LocalMachine, m_sRegCurrentPath, name, value, RegistryValueKind.DWord);
		}
	}

	private void SetHealthProtectionStatus()
	{
		if (m_HealthProtectionStatus == 0)
		{
			SetHealthProtectionHigh();
		}
		else if (m_HealthProtectionStatus == 1)
		{
			SetHealthProtectionMiddle();
		}
		else if (m_HealthProtectionStatus == 2)
		{
			SetHealthProtectionLow();
		}
	}

	private void SetHealthProtectionHigh()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1958, ref Data);
		BitArray bitArray = new BitArray(new byte[1] { Data });
		bitArray[4] = false;
		bitArray[5] = false;
		byte data = ConvertToByte(bitArray);
		EcCtrl.Write(GetType().Name, 1958, data);
	}

	private void SetHealthProtectionMiddle()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1958, ref Data);
		BitArray bitArray = new BitArray(new byte[1] { Data });
		bitArray[4] = true;
		bitArray[5] = false;
		byte data = ConvertToByte(bitArray);
		EcCtrl.Write(GetType().Name, 1958, data);
	}

	private void SetHealthProtectionLow()
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1958, ref Data);
		BitArray bitArray = new BitArray(new byte[1] { Data });
		bitArray[4] = false;
		bitArray[5] = true;
		byte data = ConvertToByte(bitArray);
		EcCtrl.Write(GetType().Name, 1958, data);
	}

	private byte ConvertToByte(BitArray bits)
	{
		_ = bits.Count;
		_ = 8;
		byte[] array = new byte[1];
		bits.CopyTo(array, 0);
		return array[0];
	}

	private void SetTypeCAdaptorSwitch(int status)
	{
		byte Data = 0;
		EcCtrl.Read(GetType().Name, 1996, ref Data);
		byte b = (byte)Convert.ToUInt64(Data);
		b = ((status != 1) ? ((byte)(b & 0x7F)) : ((byte)(b | 0x80)));
		EcCtrl.Write(GetType().Name, 1996, b);
	}

	private void SetBatteryChargingLimit_Up(int limit)
	{
		byte Data = 0;
		byte b = 128;
		byte b2 = 0;
		EcCtrl.Read(GetType().Name, 1977, ref Data);
		b2 = ((limit != 100) ? ((byte)((Data & b) + limit)) : ((byte)(Data & b)));
		EcCtrl.Write(GetType().Name, 1977, b2);
	}

	private int ReadBatteryChargingLimit_Up()
	{
		byte Data = 0;
		byte b = 127;
		byte b2 = 0;
		int num = 100;
		EcCtrl.Read(GetType().Name, 1977, ref Data);
		b2 = (byte)(Data & b);
		if (b2 == 0)
		{
			return 100;
		}
		return Convert.ToInt32(b2);
	}

	private void SetBatteryChargingLimit_Down(int limit)
	{
		byte Data = 0;
		byte b = 128;
		byte b2 = 0;
		EcCtrl.Read(GetType().Name, 2000, ref Data);
		if (limit >= 1 && limit <= 95)
		{
			b2 = (byte)((Data & b) + limit);
			EcCtrl.Write(GetType().Name, 2000, b2);
		}
	}

	private int ReadBatteryChargingLimit_Down()
	{
		byte Data = 0;
		int num = 100;
		EcCtrl.Read(GetType().Name, 2000, ref Data);
		if (Data == 0)
		{
			return 95;
		}
		return Convert.ToInt32(Data);
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
					BatteryTime = Convert.ToInt32(battry.GetCurrentBatteryLifeTime()),
					BatteryFullTime = Convert.ToInt32(battry.GetCurrentBatteryFullChargeTime())
				};
				LogCtrl.TraceMessage("BatteryPowerStatus: " + BatteryPowerStatus + ", BatteryPercent: " + battry.GetCurrentBatteryLifePercent() + ", BatteryTime: " + battry.GetCurrentBatteryLifeTime() + ", BatteryFullTime: " + battry.GetCurrentBatteryFullChargeTime(), "SystemEvents_PowerModeChanged", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySystem\\Battry\\BatteryProtection2.cs", 510);
				SendToUI(status);
			}
			else if (SystemInformation.PowerStatus.PowerLineStatus.ToString().Equals("Online"))
			{
				BatteryPowerStatus = 1u;
				var status2 = new
				{
					BatteryPowerStatus = BatteryPowerStatus,
					BatteryPercent = Convert.ToInt32(battry.GetCurrentBatteryLifePercent()),
					BatteryTime = -1,
					BatteryFullTime = Convert.ToInt32(battry.GetCurrentBatteryFullChargeTime())
				};
				LogCtrl.TraceMessage("BatteryPowerStatus: " + BatteryPowerStatus + ", BatteryPercent: " + battry.GetCurrentBatteryLifePercent() + ", BatteryTime: -1, BatteryFullTime: " + battry.GetCurrentBatteryFullChargeTime(), "SystemEvents_PowerModeChanged", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySystem\\Battry\\BatteryProtection2.cs", 526);
				SendToUI(status2);
			}
		}
		else if (e.Mode == PowerModes.Resume)
		{
			Init();
		}
		else
		{
			_ = e.Mode;
			_ = 3;
		}
	}

	private void Battry_LifePercentChange(object sender, EventArgs e)
	{
		try
		{
			int result = 65535;
			int result2 = 0;
			int result3 = 0;
			int.TryParse(sender.ToString(), out result);
			int.TryParse(battry.GetCurrentBatteryLifeTime(), out result2);
			int.TryParse(battry.GetCurrentBatteryFullChargeTime(), out result3);
			var status = new
			{
				BatteryPercent = result,
				BatteryTime = result2,
				BatteryFullTime = result3
			};
			LogCtrl.TraceMessage("BatteryPercent: " + result + ", BatteryTime: " + result2 + ", BatteryFullTime: " + battry.GetCurrentBatteryFullChargeTime(), "Battry_LifePercentChange", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySystem\\Battry\\BatteryProtection2.cs", 560);
			SendToUI(status);
		}
		catch (Exception ex)
		{
			LogCtrl.TraceMessage("Battry percent " + ex.ToString(), "Battry_LifePercentChange", "D:\\_work\\ControlCenter3_1\\Service\\MyControlCenter\\MyControlCenter\\MySystem\\Battry\\BatteryProtection2.cs", 565);
		}
	}

	private void SendToUI(dynamic status)
	{
		m_MQTTClient.Publish("System/BatteryProtection", status, false);
	}

	private void UpdateStatusToClient()
	{
		if (SystemInformation.PowerStatus.PowerLineStatus.ToString().Equals("Offline"))
		{
			BatteryPowerStatus = 0u;
			var status = new
			{
				BatteryPowerStatus = BatteryPowerStatus,
				BatteryPercent = Convert.ToInt32(battry.GetCurrentBatteryLifePercent()),
				BatteryTime = Convert.ToInt32(battry.GetCurrentBatteryLifeTime()),
				BatteryFullTime = Convert.ToInt32(battry.GetCurrentBatteryFullChargeTime()),
				HealthProtectionStatus = Convert.ToString(m_HealthProtectionStatus),
				TypeCAdaptorPrioritySwitch = Convert.ToString(m_TypeCAdaptorPrioritySwitch),
				TypeCAdaptorPrioritySupport = m_TypeCAdaptorPrioritySupport
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
				BatteryTime = -1,
				BatteryFullTime = Convert.ToInt32(battry.GetCurrentBatteryFullChargeTime()),
				HealthProtectionStatus = Convert.ToString(m_HealthProtectionStatus),
				TypeCAdaptorPrioritySwitch = Convert.ToString(m_TypeCAdaptorPrioritySwitch),
				TypeCAdaptorPrioritySupport = m_TypeCAdaptorPrioritySupport
			};
			SendToUI(status2);
		}
	}
}
