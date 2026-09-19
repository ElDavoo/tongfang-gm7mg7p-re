using Define;
using Utility;

namespace MyControlCenter.MySetting.DisplayFeature;

internal class DisplayFeatureCtrl
{
	private DisplayFeatureManager m_Manager;

	private static readonly DisplayFeatureCtrl control = new DisplayFeatureCtrl();

	public static DisplayFeatureCtrl Instance => control;

	public DisplayFeatureCtrl()
	{
		RegistryCtrl.GetCustomizeTarget();
		switch (RegistryCtrl.GetBridgeType())
		{
		case 0:
			m_Manager = new DisplayFeatureManager();
			break;
		case 1:
			m_Manager = new DisplayFeatureManager_Intel();
			break;
		default:
			m_Manager = new DisplayFeatureManager();
			break;
		}
	}

	public DisplayModeParams GamingModePara()
	{
		return m_Manager.GamingModePara;
	}

	public DisplayModeParams VideoModePara()
	{
		return m_Manager.VideoModePara;
	}

	public DisplayModeParams ReadModePara()
	{
		return m_Manager.ReadModePara;
	}

	public DisplayModeParams CutomizedModePara()
	{
		return m_Manager.CutomizedModePara;
	}

	public void LoadRegistry()
	{
		m_Manager.LoadRegistry();
	}

	public void LoadDefaultRegistry()
	{
		m_Manager.LoadDefaultRegistry();
	}

	public void Default(string mode)
	{
		m_Manager.Default(mode);
	}

	public void SetDisplayStdandardMode()
	{
		m_Manager.SetDisplayStdandardMode();
	}

	public void SetDisplayGamingModeFromReg()
	{
		m_Manager.SetDisplayGamingModeFromReg();
	}

	public void SetDisplayVideoModeFromReg()
	{
		m_Manager.SetDisplayVideoModeFromReg();
	}

	public void SetDisplayReadModeFromReg()
	{
		m_Manager.SetDisplayReadModeFromReg();
	}

	public void SetDisplayCustomizedModeFromReg()
	{
		m_Manager.SetDisplayCustomizedModeFromReg();
	}

	public void SetDisplayGamingModeValue(dynamic data)
	{
		m_Manager.SetDisplayGamingModeValue(data);
	}

	public void SetDisplayVideoModeValue(dynamic data)
	{
		m_Manager.SetDisplayVideoModeValue(data);
	}

	public void SetDisplayReadModeValue(dynamic data)
	{
		m_Manager.SetDisplayReadModeValue(data);
	}

	public void SetDisplayCustomizedModeValue(dynamic data)
	{
		m_Manager.SetDisplayCustomizedModeValue(data);
	}
}
