using Utility;

namespace MyControlCenter;

public class MySystemCtrl
{
	private MySystemManager m_Manager;

	public void DisableByService()
	{
		m_Manager.Disable();
	}

	public MySystemCtrl()
	{
		int customizeTarget = RegistryCtrl.GetCustomizeTarget();
		switch (RegistryCtrl.GetBridgeType())
		{
		case 0:
			m_Manager = new MySystemManager();
			break;
		case 1:
			_ = 1;
			m_Manager = new MySystemManager();
			break;
		default:
			m_Manager = new MySystemManager();
			break;
		}
		m_Manager.InitTimers();
	}

	~MySystemCtrl()
	{
	}

	public void Dispose()
	{
		m_Manager.Dispose();
	}

	internal void Receive(byte[] message)
	{
		m_Manager.Receive(message);
	}
}
