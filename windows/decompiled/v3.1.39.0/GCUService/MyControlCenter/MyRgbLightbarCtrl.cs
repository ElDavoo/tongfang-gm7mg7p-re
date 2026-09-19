using Utility;

namespace MyControlCenter;

public class MyRgbLightbarCtrl
{
	private MyRgbLightbarManager m_Manager;

	private static readonly MyRgbLightbarCtrl control = new MyRgbLightbarCtrl();

	public static MyRgbLightbarCtrl Instance => control;

	public MyRgbLightbarCtrl()
	{
		int customizeTarget = RegistryCtrl.GetCustomizeTarget();
		switch (RegistryCtrl.GetBridgeType())
		{
		case 0:
			m_Manager = new MyRgbLightbarManager();
			break;
		case 1:
			_ = 1;
			m_Manager = new MyRgbLightbarManager();
			break;
		default:
			m_Manager = new MyRgbLightbarManager();
			break;
		}
	}

	public void Recieve(byte[] data)
	{
		m_Manager.Recieve(data);
	}

	public void EnableByService()
	{
		m_Manager.Enable();
	}

	public void DisableByService()
	{
		m_Manager.Disable();
	}

	public void Resume()
	{
		m_Manager.Resume();
		m_Manager.UpdateStatusToClient(1);
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
		m_Manager.Default();
	}

	public uint GetPowerStatus()
	{
		return m_Manager.GetPowerStatus();
	}
}
