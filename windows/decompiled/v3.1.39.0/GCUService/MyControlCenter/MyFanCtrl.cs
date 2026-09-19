using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Threading;
using MyControlCenter.FanModel;
using MyControlCenter.MyFan;
using MyECIO;
using Utility;

namespace MyControlCenter;

public class MyFanCtrl
{
	public MyFanManager m_Manager;

	private static readonly MyFanCtrl control = new MyFanCtrl();

	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private Thread fanThread;

	public static MyFanCtrl Instance => control;

	public MyFanCtrl()
	{
		int customizeTarget = RegistryCtrl.GetCustomizeTarget();
		int bridgeType = RegistryCtrl.GetBridgeType();
		if (!EcCtrl.IsSuportRamFan1p5())
		{
			switch (bridgeType)
			{
			case 0:
				m_Manager = new MyFanManager();
				break;
			case 1:
				_ = 1;
				m_Manager = new MyFanManager();
				break;
			default:
				m_Manager = new MyFanManager();
				break;
			}
		}
		else if (!EcCtrl.GetProjectIdFromEC().IsProjectId_Commercial())
		{
			if (customizeTarget == 42)
			{
				m_Manager = new MyFanManager_RamFan1p5_NV();
			}
			else
			{
				m_Manager = new MyFanManager_RamFan1p5();
			}
		}
		else
		{
			switch (customizeTarget)
			{
			case 11:
				m_Manager = new MyFanManager_RamFan1p5_Normal();
				break;
			case 42:
				m_Manager = new MyFanManager_RamFan1p5_NV();
				break;
			default:
				m_Manager = new MyFanManager_RamFan1p5_CML();
				break;
			}
		}
	}

	public void Receive(byte[] data)
	{
		m_Manager.Receive(data);
	}

	private void TestAI(bool start, string modelname = "000")
	{
		if (start && fanThread == null)
		{
			Task.Run(delegate
			{
				fanThread = new Thread((ThreadStart)delegate
				{
					CPUInfo cPUInfo = new CPUInfo();
					List<ModelType> list = new List<ModelType>();
					int lasDuty = 30;
					double num = 0.0;
					double num2 = 0.0;
					while (start)
					{
						int cPUUsage = cPUInfo.GetCPUUsage();
						int cPUTemperature = cPUInfo.GetCPUTemperature();
						list.Add(new ModelType
						{
							CPUTemp = cPUTemperature,
							CPUUsage = cPUUsage
						});
						if (list.Count > 500)
						{
							list.RemoveAt(0);
						}
						if (list.Count > 10)
						{
							BaseFanModel baseFanModel = ((!(modelname == "001")) ? ((BaseFanModel)new FanModel_000("000", "Cpu", list)) : ((BaseFanModel)new FanModel_001("001", "Cpu", list)));
							List<int> list2 = new List<int>();
							foreach (ModelType item in list)
							{
								_ = item;
								list2.Add(0);
							}
							baseFanModel.setPostionList(list2);
							baseFanModel.Run(lasDuty);
							baseFanModel.GetPosition();
							lasDuty = baseFanModel.GetPosition().Last();
							num2 = baseFanModel.GetResult().Last() / 100.0;
						}
						try
						{
							_ = new
							{
								Mode = "FAN_OFFICE_MODE_ADV_LV3_PWMS",
								T1 = lasDuty.ToString(),
								T2 = lasDuty.ToString(),
								T3 = lasDuty.ToString(),
								T4 = lasDuty.ToString(),
								T5 = lasDuty.ToString()
							};
							num += num2;
							m_Manager.UpdateStatusToClient(1, Convert.ToInt32(num), cPUTemperature);
						}
						catch (Exception)
						{
						}
						Thread.Sleep(2000);
					}
				});
				fanThread.Start();
			});
		}
		else
		{
			fanThread?.Abort();
			fanThread = null;
		}
	}

	public int GetTurboModeSupportFlag()
	{
		return m_Manager.GetTurboModeSupportFlag();
	}

	public void EnableByService(Dispatcher dispatcher)
	{
		m_Manager.EnableByService(dispatcher);
	}

	public void DisableByService()
	{
		m_Manager.Disable();
	}

	public void Resume()
	{
		m_Manager.Resume();
	}

	public void OnModernStandby()
	{
		m_Manager.OnModernStandby();
	}

	public void PowerStatusChange(int mode)
	{
		m_Manager.PowerStatusChange(mode);
		m_Manager.UpdateStatusToClient(1);
	}

	public void Uninstall()
	{
		m_Manager.Uninstall();
	}

	public void Restore()
	{
		m_Manager.Restore();
	}

	public void ModeSwitchChanged()
	{
		m_Manager.ModeSwitchChanged();
	}

	public void FanBoostUpdate()
	{
		m_Manager.FanBoostUpdate();
	}

	public void FanBoostOffFromEC()
	{
		m_Manager.FanBoostOffFromEC();
	}

	public void SetPairedProfileIndex(uint index)
	{
		m_Manager.SetPairedProfileIndex(index);
	}

	public void SafetyProtectionUpdate()
	{
		m_Manager.SafetyProtectionUpdate();
	}

	public void WhisperUpdate()
	{
		m_Manager.WhisperUpdate();
	}
}
