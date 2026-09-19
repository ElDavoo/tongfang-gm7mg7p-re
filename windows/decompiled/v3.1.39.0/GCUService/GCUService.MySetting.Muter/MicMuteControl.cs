using System;
using System.Reflection;
using AudioLib;
using MyECIO;

namespace GCUService.MySetting.Muter;

public class MicMuteControl
{
	private static string m_className = "[" + MethodBase.GetCurrentMethod().DeclaringType.Name + "] ";

	private MyEcCtrl EcCtrl = MyEcCtrl.Instance;

	private static readonly MicMuteControl micadudiomodel = new MicMuteControl();

	private bool m_bMute;

	public static MicMuteControl Instance => micadudiomodel;

	public void Init()
	{
		AudioData.Instance.InitInputDevice();
		AudioData.Instance.InputDeviceMuteEvent -= Instance_InputDeviceMuteEvent;
		AudioData.Instance.InputDeviceMuteEvent += Instance_InputDeviceMuteEvent;
		m_bMute = AudioData.Instance.GetInputDeviceMute();
		SetLED(m_bMute);
	}

	private void Instance_InputDeviceMuteEvent(object sender, EventArgs e)
	{
		m_bMute = (bool)sender;
		SetLED(m_bMute);
	}

	public void Trigger()
	{
		m_bMute = AudioData.Instance.GetInputDeviceMute();
		m_bMute = !m_bMute;
		AudioData.Instance.SetInputDeviceMute(m_bMute);
	}

	private void SetLED(bool bMute)
	{
		byte Data = 0;
		EcCtrl.Read(m_className, 1958, ref Data);
		byte b = (byte)Convert.ToUInt64(Data);
		b = ((!bMute) ? ((byte)(b & 0xFB)) : ((byte)(b | 4)));
		EcCtrl.Write(m_className, 1958, b);
	}
}
