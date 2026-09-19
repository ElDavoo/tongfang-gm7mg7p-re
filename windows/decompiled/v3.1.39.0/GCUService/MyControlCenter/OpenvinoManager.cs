using System.Text;
using Utility;

namespace MyControlCenter;

internal class OpenvinoManager
{
	private static HandWave hand;

	private static FaceDetection face;

	public static async void Receive(byte[] message)
	{
		await Json.ToObjectAsync<object>(Encoding.UTF8.GetString(message));
	}
}
