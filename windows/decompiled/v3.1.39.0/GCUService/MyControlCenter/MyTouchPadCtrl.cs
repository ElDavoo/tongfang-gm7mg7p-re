using Utility;

namespace MyControlCenter;

public class MyTouchPadCtrl
{
	public MyTouchPadManager m_Manager;

	private static readonly MyTouchPadCtrl control = new MyTouchPadCtrl();

	public static MyTouchPadCtrl Instance => control;

	public MyTouchPadCtrl()
	{
		m_Manager = new MyTouchPadManager();
		string bIOSProjectID = RegistryCtrl.GetBIOSProjectID();
		if (bIOSProjectID != null && bIOSProjectID == "IDM")
		{
			m_Manager.Init_IDM_TouchPadSetting();
		}
	}

	public void Receive(byte[] data)
	{
		m_Manager.Receive(data);
	}

	public void EnableByService()
	{
		m_Manager.EnableByService();
	}

	public void DisableByService()
	{
		m_Manager.Disable();
	}

	public void Resume()
	{
		m_Manager.Resume();
	}

	public void Uninstall()
	{
		m_Manager.Uninstall();
	}

	public void Restore()
	{
		m_Manager.Restore();
	}
}
