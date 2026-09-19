using MyECIO;
using Utility;

namespace MyControlCenter.MyFan.FanTable;

public class MyFanTableCtrl
{
	private FanTable_Manager1p5 m_Manager;

	private static readonly MyFanTableCtrl control = new MyFanTableCtrl();

	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private BackgroundQueue backgroundQueue = new BackgroundQueue();

	public static MyFanTableCtrl Instance => control;

	public MyFanTableCtrl()
	{
		int customizeTarget = RegistryCtrl.GetCustomizeTarget();
		if (EcCtrl.IsSuportRamFan1p5())
		{
			if (!EcCtrl.GetProjectIdFromEC().IsProjectId_Commercial())
			{
				m_Manager = new FanTable_Manager1p5();
			}
			else if (customizeTarget == 11)
			{
				m_Manager = null;
			}
			else
			{
				m_Manager = new FanTable_Manager1p5_CML();
			}
		}
	}

	public bool GetFanTableInit()
	{
		if (m_Manager != null)
		{
			return m_Manager.GetFanTableInit();
		}
		return false;
	}

	public void FanTable_Init()
	{
		if (m_Manager != null)
		{
			m_Manager?.FanTable_Init();
		}
	}

	public void DisableByService()
	{
		SetFanControlByRamFan1p5(status: false);
		m_Manager.ClearFanTableAll();
	}

	public void Resume()
	{
	}

	public void Uninstall()
	{
		SetFanControlByRamFan1p5(status: false);
		m_Manager.ClearFanTableAll();
	}

	public void GetFanTable(string _name)
	{
		m_Manager.GetFanTable(_name);
	}

	public void SetFanTable(string _name)
	{
		backgroundQueue.QueueTask(delegate
		{
			SetFanControlByRamFan1p5(status: false);
			m_Manager.SetFanTable(_name);
			SetFanControlByRamFan1p5(status: true);
		});
	}

	public void SetFanTableSetting(dynamic data, bool saveEC = true)
	{
		m_Manager.SetFanTableSetting(data, saveEC);
	}

	public void SetFanControlRespective(dynamic data)
	{
		m_Manager.SetFanControlRespective(data);
	}

	public void RestoreDefaultFanTableAll()
	{
		m_Manager.RestoreDefaultFanTableAll();
	}

	public void RestoreDefaultFanTable(dynamic data)
	{
		m_Manager.RestoreDefaultFanTable(data);
	}

	public void GetPLDefaultValue(string name, ref string PL1, ref string PL2, ref string PL1_dc, ref string PL2_dc)
	{
		m_Manager.GetPLDefaultValue(name, ref PL1, ref PL2, ref PL1_dc, ref PL2_dc);
	}

	public void GetGpuFeatureDefaultValue(string name, ref string DB, ref string WM)
	{
		m_Manager.GetGpuFeatureDefaultValue(name, ref DB, ref WM);
	}

	private void SetFanControlByRamFan1p5(bool status)
	{
		byte Data = 0;
		byte b = 251;
		byte b2 = 0;
		byte b3 = 0;
		b2 = (byte)(status ? 4 : 0);
		EcCtrl.Read(GetType().Name, 1990, ref Data);
		b3 = (byte)((Data & b) + b2);
		EcCtrl.Write(GetType().Name, 1990, b3);
	}
}
