using Utility;

namespace MyControlCenter;

public class MySettingCtrl
{
	public MySettingManager m_Manager;

	public MySettingCtrl()
	{
		int customizeTarget = RegistryCtrl.GetCustomizeTarget();
		switch (RegistryCtrl.GetBridgeType())
		{
		case 0:
			m_Manager = new MySettingManager();
			break;
		case 1:
			_ = 1;
			m_Manager = new MySettingManager();
			break;
		default:
			m_Manager = new MySettingManager();
			break;
		}
	}

	public void Recieve(byte[] data)
	{
		m_Manager.Receive(data);
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

	public void PowerStatusChange(int mode)
	{
	}

	public void Uninstall()
	{
		m_Manager.Uninstall();
	}

	public void DeleteAllPowerPlan()
	{
		m_Manager.DeleteAllPowerPlan();
	}

	public void Restore()
	{
		m_Manager.Restore();
	}
}
