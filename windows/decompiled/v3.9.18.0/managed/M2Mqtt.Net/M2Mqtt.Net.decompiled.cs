using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Security;
using System.Net.Sockets;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.Versioning;
using System.Security.Authentication;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Threading;
using uPLibrary.Networking.M2Mqtt.Exceptions;
using uPLibrary.Networking.M2Mqtt.Internal;
using uPLibrary.Networking.M2Mqtt.Messages;
using uPLibrary.Networking.M2Mqtt.Session;
using uPLibrary.Networking.M2Mqtt.Utility;

[assembly: CompilationRelaxations(8)]
[assembly: RuntimeCompatibility(WrapNonExceptionThrows = true)]
[assembly: Debuggable(DebuggableAttribute.DebuggingModes.IgnoreSymbolStoreSequencePoints)]
[assembly: AssemblyTitle("M2Mqtt")]
[assembly: AssemblyDescription("MQTT Client Library for M2M communication")]
[assembly: AssemblyConfiguration("")]
[assembly: AssemblyCompany("Paolo Patierno")]
[assembly: AssemblyProduct("M2Mqtt")]
[assembly: AssemblyCopyright("Copyright © Paolo Patierno 2014")]
[assembly: AssemblyTrademark("")]
[assembly: AssemblyFileVersion("4.3.0.0")]
[assembly: TargetFramework(".NETFramework,Version=v4.5", FrameworkDisplayName = ".NET Framework 4.5")]
[assembly: AssemblyVersion("4.3.0.0")]
namespace uPLibrary.Networking.M2Mqtt
{
	public interface IMqttNetworkChannel
	{
		bool DataAvailable { get; }

		int Receive(byte[] buffer);

		int Receive(byte[] buffer, int timeout);

		int Send(byte[] buffer);

		void Close();

		void Connect();

		void Accept();
	}
	public class MqttClient
	{
		public delegate void MqttMsgPublishEventHandler(object sender, MqttMsgPublishEventArgs e);

		public delegate void MqttMsgPublishedEventHandler(object sender, MqttMsgPublishedEventArgs e);

		public delegate void MqttMsgSubscribedEventHandler(object sender, MqttMsgSubscribedEventArgs e);

		public delegate void MqttMsgUnsubscribedEventHandler(object sender, MqttMsgUnsubscribedEventArgs e);

		public delegate void ConnectionClosedEventHandler(object sender, EventArgs e);

		internal class MqttMsgContextFinder
		{
			internal ushort MessageId { get; set; }

			internal MqttMsgFlow Flow { get; set; }

			internal MqttMsgContextFinder(ushort messageId, MqttMsgFlow flow)
			{
				MessageId = messageId;
				Flow = flow;
			}

			internal bool Find(object item)
			{
				MqttMsgContext mqttMsgContext = (MqttMsgContext)item;
				if (mqttMsgContext.Message.Type == 3 && mqttMsgContext.Message.MessageId == MessageId)
				{
					return mqttMsgContext.Flow == Flow;
				}
				return false;
			}
		}

		private string brokerHostName;

		private int brokerPort;

		private bool isRunning;

		private AutoResetEvent receiveEventWaitHandle;

		private AutoResetEvent inflightWaitHandle;

		private AutoResetEvent syncEndReceiving;

		private MqttMsgBase msgReceived;

		private Exception exReceiving;

		private int keepAlivePeriod;

		private AutoResetEvent keepAliveEvent;

		private AutoResetEvent keepAliveEventEnd;

		private int lastCommTime;

		private IMqttNetworkChannel channel;

		private Queue inflightQueue;

		private Queue internalQueue;

		private Queue eventQueue;

		private MqttClientSession session;

		private MqttSettings settings;

		private ushort messageIdCounter;

		private bool isConnectionClosing;

		public bool IsConnected { get; private set; }

		public string ClientId { get; private set; }

		public bool CleanSession { get; private set; }

		public bool WillFlag { get; private set; }

		public byte WillQosLevel { get; private set; }

		public string WillTopic { get; private set; }

		public string WillMessage { get; private set; }

		public MqttProtocolVersion ProtocolVersion { get; set; }

		public MqttSettings Settings => settings;

		public event MqttMsgPublishEventHandler MqttMsgPublishReceived;

		public event MqttMsgPublishedEventHandler MqttMsgPublished;

		public event MqttMsgSubscribedEventHandler MqttMsgSubscribed;

		public event MqttMsgUnsubscribedEventHandler MqttMsgUnsubscribed;

		public event ConnectionClosedEventHandler ConnectionClosed;

		[Obsolete("Use this ctor MqttClient(string brokerHostName) insted")]
		public MqttClient(IPAddress brokerIpAddress)
			: this(brokerIpAddress, 1883, secure: false, null, null, MqttSslProtocols.None)
		{
		}

		[Obsolete("Use this ctor MqttClient(string brokerHostName, int brokerPort, bool secure, X509Certificate caCert) insted")]
		public MqttClient(IPAddress brokerIpAddress, int brokerPort, bool secure, X509Certificate caCert, X509Certificate clientCert, MqttSslProtocols sslProtocol)
		{
			Init(brokerIpAddress.ToString(), brokerPort, secure, caCert, clientCert, sslProtocol, null, null);
		}

		public MqttClient(string brokerHostName)
			: this(brokerHostName, 1883, secure: false, null, null, MqttSslProtocols.None)
		{
		}

		public MqttClient(string brokerHostName, int brokerPort, bool secure, X509Certificate caCert, X509Certificate clientCert, MqttSslProtocols sslProtocol)
		{
			Init(brokerHostName, brokerPort, secure, caCert, clientCert, sslProtocol, null, null);
		}

		public MqttClient(string brokerHostName, int brokerPort, bool secure, X509Certificate caCert, X509Certificate clientCert, MqttSslProtocols sslProtocol, RemoteCertificateValidationCallback userCertificateValidationCallback)
			: this(brokerHostName, brokerPort, secure, caCert, clientCert, sslProtocol, userCertificateValidationCallback, null)
		{
		}

		public MqttClient(string brokerHostName, int brokerPort, bool secure, MqttSslProtocols sslProtocol, RemoteCertificateValidationCallback userCertificateValidationCallback, LocalCertificateSelectionCallback userCertificateSelectionCallback)
			: this(brokerHostName, brokerPort, secure, null, null, sslProtocol, userCertificateValidationCallback, userCertificateSelectionCallback)
		{
		}

		public MqttClient(string brokerHostName, int brokerPort, bool secure, X509Certificate caCert, X509Certificate clientCert, MqttSslProtocols sslProtocol, RemoteCertificateValidationCallback userCertificateValidationCallback, LocalCertificateSelectionCallback userCertificateSelectionCallback)
		{
			Init(brokerHostName, brokerPort, secure, caCert, clientCert, sslProtocol, userCertificateValidationCallback, userCertificateSelectionCallback);
		}

		private void Init(string brokerHostName, int brokerPort, bool secure, X509Certificate caCert, X509Certificate clientCert, MqttSslProtocols sslProtocol, RemoteCertificateValidationCallback userCertificateValidationCallback, LocalCertificateSelectionCallback userCertificateSelectionCallback)
		{
			ProtocolVersion = MqttProtocolVersion.Version_3_1_1;
			this.brokerHostName = brokerHostName;
			this.brokerPort = brokerPort;
			settings = MqttSettings.Instance;
			if (!secure)
			{
				settings.Port = this.brokerPort;
			}
			else
			{
				settings.SslPort = this.brokerPort;
			}
			syncEndReceiving = new AutoResetEvent(initialState: false);
			keepAliveEvent = new AutoResetEvent(initialState: false);
			inflightWaitHandle = new AutoResetEvent(initialState: false);
			inflightQueue = new Queue();
			receiveEventWaitHandle = new AutoResetEvent(initialState: false);
			eventQueue = new Queue();
			internalQueue = new Queue();
			session = null;
			channel = new MqttNetworkChannel(this.brokerHostName, this.brokerPort, secure, caCert, clientCert, sslProtocol, userCertificateValidationCallback, userCertificateSelectionCallback);
		}

		public byte Connect(string clientId)
		{
			return Connect(clientId, null, null, willRetain: false, 0, willFlag: false, null, null, cleanSession: true, 60);
		}

		public byte Connect(string clientId, string username, string password)
		{
			return Connect(clientId, username, password, willRetain: false, 0, willFlag: false, null, null, cleanSession: true, 60);
		}

		public byte Connect(string clientId, string username, string password, bool cleanSession, ushort keepAlivePeriod)
		{
			return Connect(clientId, username, password, willRetain: false, 0, willFlag: false, null, null, cleanSession, keepAlivePeriod);
		}

		public byte Connect(string clientId, string username, string password, bool willRetain, byte willQosLevel, bool willFlag, string willTopic, string willMessage, bool cleanSession, ushort keepAlivePeriod)
		{
			MqttMsgConnect msg = new MqttMsgConnect(clientId, username, password, willRetain, willQosLevel, willFlag, willTopic, willMessage, cleanSession, keepAlivePeriod, (byte)ProtocolVersion);
			try
			{
				channel.Connect();
			}
			catch (Exception innerException)
			{
				throw new MqttConnectionException("Exception connecting to the broker", innerException);
			}
			lastCommTime = 0;
			isRunning = true;
			isConnectionClosing = false;
			Fx.StartThread(ReceiveThread);
			MqttMsgConnack obj = (MqttMsgConnack)SendReceive(msg);
			if (obj.ReturnCode == 0)
			{
				ClientId = clientId;
				CleanSession = cleanSession;
				WillFlag = willFlag;
				WillTopic = willTopic;
				WillMessage = willMessage;
				WillQosLevel = willQosLevel;
				this.keepAlivePeriod = keepAlivePeriod * 1000;
				RestoreSession();
				if (this.keepAlivePeriod != 0)
				{
					Fx.StartThread(KeepAliveThread);
				}
				Fx.StartThread(DispatchEventThread);
				Fx.StartThread(ProcessInflightThread);
				IsConnected = true;
			}
			return obj.ReturnCode;
		}

		public void Disconnect()
		{
			MqttMsgDisconnect msg = new MqttMsgDisconnect();
			Send(msg);
			OnConnectionClosing();
		}

		private void Close()
		{
			isRunning = false;
			if (receiveEventWaitHandle != null)
			{
				receiveEventWaitHandle.Set();
			}
			if (inflightWaitHandle != null)
			{
				inflightWaitHandle.Set();
			}
			keepAliveEvent.Set();
			if (keepAliveEventEnd != null)
			{
				keepAliveEventEnd.WaitOne();
			}
			inflightQueue.Clear();
			internalQueue.Clear();
			eventQueue.Clear();
			channel.Close();
			IsConnected = false;
		}

		private MqttMsgPingResp Ping()
		{
			MqttMsgPingReq msg = new MqttMsgPingReq();
			try
			{
				return (MqttMsgPingResp)SendReceive(msg, keepAlivePeriod);
			}
			catch (Exception ex)
			{
				uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Error, "Exception occurred: {0}", ex.ToString());
				OnConnectionClosing();
				return null;
			}
		}

		public ushort Subscribe(string[] topics, byte[] qosLevels)
		{
			MqttMsgSubscribe mqttMsgSubscribe = new MqttMsgSubscribe(topics, qosLevels);
			mqttMsgSubscribe.MessageId = GetMessageId();
			EnqueueInflight(mqttMsgSubscribe, MqttMsgFlow.ToPublish);
			return mqttMsgSubscribe.MessageId;
		}

		public ushort Unsubscribe(string[] topics)
		{
			MqttMsgUnsubscribe mqttMsgUnsubscribe = new MqttMsgUnsubscribe(topics);
			mqttMsgUnsubscribe.MessageId = GetMessageId();
			EnqueueInflight(mqttMsgUnsubscribe, MqttMsgFlow.ToPublish);
			return mqttMsgUnsubscribe.MessageId;
		}

		public ushort Publish(string topic, byte[] message)
		{
			return Publish(topic, message, 0, retain: false);
		}

		public ushort Publish(string topic, byte[] message, byte qosLevel, bool retain)
		{
			MqttMsgPublish mqttMsgPublish = new MqttMsgPublish(topic, message, dupFlag: false, qosLevel, retain);
			mqttMsgPublish.MessageId = GetMessageId();
			if (EnqueueInflight(mqttMsgPublish, MqttMsgFlow.ToPublish))
			{
				return mqttMsgPublish.MessageId;
			}
			throw new MqttClientException(MqttClientErrorCode.InflightQueueFull);
		}

		private void OnInternalEvent(InternalEvent internalEvent)
		{
			lock (eventQueue)
			{
				eventQueue.Enqueue(internalEvent);
			}
			receiveEventWaitHandle.Set();
		}

		private void OnConnectionClosing()
		{
			if (!isConnectionClosing)
			{
				isConnectionClosing = true;
				receiveEventWaitHandle.Set();
			}
		}

		private void OnMqttMsgPublishReceived(MqttMsgPublish publish)
		{
			if (this.MqttMsgPublishReceived != null)
			{
				this.MqttMsgPublishReceived(this, new MqttMsgPublishEventArgs(publish.Topic, publish.Message, publish.DupFlag, publish.QosLevel, publish.Retain));
			}
		}

		private void OnMqttMsgPublished(ushort messageId, bool isPublished)
		{
			if (this.MqttMsgPublished != null)
			{
				this.MqttMsgPublished(this, new MqttMsgPublishedEventArgs(messageId, isPublished));
			}
		}

		private void OnMqttMsgSubscribed(MqttMsgSuback suback)
		{
			if (this.MqttMsgSubscribed != null)
			{
				this.MqttMsgSubscribed(this, new MqttMsgSubscribedEventArgs(suback.MessageId, suback.GrantedQoSLevels));
			}
		}

		private void OnMqttMsgUnsubscribed(ushort messageId)
		{
			if (this.MqttMsgUnsubscribed != null)
			{
				this.MqttMsgUnsubscribed(this, new MqttMsgUnsubscribedEventArgs(messageId));
			}
		}

		private void OnConnectionClosed()
		{
			if (this.ConnectionClosed != null)
			{
				this.ConnectionClosed(this, EventArgs.Empty);
			}
		}

		private void Send(byte[] msgBytes)
		{
			try
			{
				channel.Send(msgBytes);
				lastCommTime = Environment.TickCount;
			}
			catch (Exception ex)
			{
				uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Error, "Exception occurred: {0}", ex.ToString());
				throw new MqttCommunicationException(ex);
			}
		}

		private void Send(MqttMsgBase msg)
		{
			uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Frame, "SEND {0}", msg);
			Send(msg.GetBytes((byte)ProtocolVersion));
		}

		private MqttMsgBase SendReceive(byte[] msgBytes)
		{
			return SendReceive(msgBytes, 30000);
		}

		private MqttMsgBase SendReceive(byte[] msgBytes, int timeout)
		{
			syncEndReceiving.Reset();
			try
			{
				channel.Send(msgBytes);
				lastCommTime = Environment.TickCount;
			}
			catch (Exception ex)
			{
				if (typeof(SocketException) == ex.GetType() && ((SocketException)ex).SocketErrorCode == SocketError.ConnectionReset)
				{
					IsConnected = false;
				}
				uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Error, "Exception occurred: {0}", ex.ToString());
				throw new MqttCommunicationException(ex);
			}
			if (syncEndReceiving.WaitOne(timeout))
			{
				if (exReceiving == null)
				{
					return msgReceived;
				}
				throw exReceiving;
			}
			throw new MqttCommunicationException();
		}

		private MqttMsgBase SendReceive(MqttMsgBase msg)
		{
			return SendReceive(msg, 30000);
		}

		private MqttMsgBase SendReceive(MqttMsgBase msg, int timeout)
		{
			uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Frame, "SEND {0}", msg);
			return SendReceive(msg.GetBytes((byte)ProtocolVersion), timeout);
		}

		private bool EnqueueInflight(MqttMsgBase msg, MqttMsgFlow flow)
		{
			bool flag = true;
			if (msg.Type == 3 && msg.QosLevel == 2)
			{
				lock (inflightQueue)
				{
					MqttMsgContextFinder mqttMsgContextFinder = new MqttMsgContextFinder(msg.MessageId, MqttMsgFlow.ToAcknowledge);
					MqttMsgContext mqttMsgContext = (MqttMsgContext)inflightQueue.Get(mqttMsgContextFinder.Find);
					if (mqttMsgContext != null)
					{
						mqttMsgContext.State = MqttMsgState.QueuedQos2;
						mqttMsgContext.Flow = MqttMsgFlow.ToAcknowledge;
						flag = false;
					}
				}
			}
			if (flag)
			{
				MqttMsgState state = MqttMsgState.QueuedQos0;
				switch (msg.QosLevel)
				{
				case 0:
					state = MqttMsgState.QueuedQos0;
					break;
				case 1:
					state = MqttMsgState.QueuedQos1;
					break;
				case 2:
					state = MqttMsgState.QueuedQos2;
					break;
				}
				if (msg.Type == 8)
				{
					state = MqttMsgState.SendSubscribe;
				}
				else if (msg.Type == 10)
				{
					state = MqttMsgState.SendUnsubscribe;
				}
				MqttMsgContext mqttMsgContext2 = new MqttMsgContext
				{
					Message = msg,
					State = state,
					Flow = flow,
					Attempt = 0
				};
				lock (inflightQueue)
				{
					flag = inflightQueue.Count < settings.InflightQueueSize;
					if (flag)
					{
						inflightQueue.Enqueue(mqttMsgContext2);
						uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Queuing, "enqueued {0}", msg);
						if (msg.Type == 3)
						{
							if (mqttMsgContext2.Flow == MqttMsgFlow.ToPublish && (msg.QosLevel == 1 || msg.QosLevel == 2))
							{
								if (session != null)
								{
									session.InflightMessages.Add(mqttMsgContext2.Key, mqttMsgContext2);
								}
							}
							else if (mqttMsgContext2.Flow == MqttMsgFlow.ToAcknowledge && msg.QosLevel == 2 && session != null)
							{
								session.InflightMessages.Add(mqttMsgContext2.Key, mqttMsgContext2);
							}
						}
					}
				}
			}
			inflightWaitHandle.Set();
			return flag;
		}

		private void EnqueueInternal(MqttMsgBase msg)
		{
			bool flag = true;
			if (msg.Type == 6)
			{
				lock (inflightQueue)
				{
					MqttMsgContextFinder mqttMsgContextFinder = new MqttMsgContextFinder(msg.MessageId, MqttMsgFlow.ToAcknowledge);
					if ((MqttMsgContext)inflightQueue.Get(mqttMsgContextFinder.Find) == null)
					{
						MqttMsgPubcomp mqttMsgPubcomp = new MqttMsgPubcomp();
						mqttMsgPubcomp.MessageId = msg.MessageId;
						Send(mqttMsgPubcomp);
						flag = false;
					}
				}
			}
			else if (msg.Type == 7)
			{
				lock (inflightQueue)
				{
					MqttMsgContextFinder mqttMsgContextFinder2 = new MqttMsgContextFinder(msg.MessageId, MqttMsgFlow.ToPublish);
					if ((MqttMsgContext)inflightQueue.Get(mqttMsgContextFinder2.Find) == null)
					{
						flag = false;
					}
				}
			}
			else if (msg.Type == 5)
			{
				lock (inflightQueue)
				{
					MqttMsgContextFinder mqttMsgContextFinder3 = new MqttMsgContextFinder(msg.MessageId, MqttMsgFlow.ToPublish);
					if ((MqttMsgContext)inflightQueue.Get(mqttMsgContextFinder3.Find) == null)
					{
						flag = false;
					}
				}
			}
			if (flag)
			{
				lock (internalQueue)
				{
					internalQueue.Enqueue(msg);
					uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Queuing, "enqueued {0}", msg);
					inflightWaitHandle.Set();
				}
			}
		}

		private void ReceiveThread()
		{
			byte[] array = new byte[1];
			while (isRunning)
			{
				try
				{
					if (channel.Receive(array) > 0)
					{
						switch ((byte)((array[0] & 0xF0) >> 4))
						{
						case 1:
							throw new MqttClientException(MqttClientErrorCode.WrongBrokerMessage);
						case 2:
							msgReceived = MqttMsgConnack.Parse(array[0], (byte)ProtocolVersion, channel);
							uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Frame, "RECV {0}", msgReceived);
							syncEndReceiving.Set();
							break;
						case 12:
							throw new MqttClientException(MqttClientErrorCode.WrongBrokerMessage);
						case 13:
							msgReceived = MqttMsgPingResp.Parse(array[0], (byte)ProtocolVersion, channel);
							uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Frame, "RECV {0}", msgReceived);
							syncEndReceiving.Set();
							break;
						case 8:
							throw new MqttClientException(MqttClientErrorCode.WrongBrokerMessage);
						case 9:
						{
							MqttMsgSuback mqttMsgSuback = MqttMsgSuback.Parse(array[0], (byte)ProtocolVersion, channel);
							uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Frame, "RECV {0}", mqttMsgSuback);
							EnqueueInternal(mqttMsgSuback);
							break;
						}
						case 3:
						{
							MqttMsgPublish mqttMsgPublish = MqttMsgPublish.Parse(array[0], (byte)ProtocolVersion, channel);
							uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Frame, "RECV {0}", mqttMsgPublish);
							EnqueueInflight(mqttMsgPublish, MqttMsgFlow.ToAcknowledge);
							break;
						}
						case 4:
						{
							MqttMsgPuback mqttMsgPuback = MqttMsgPuback.Parse(array[0], (byte)ProtocolVersion, channel);
							uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Frame, "RECV {0}", mqttMsgPuback);
							EnqueueInternal(mqttMsgPuback);
							break;
						}
						case 5:
						{
							MqttMsgPubrec mqttMsgPubrec = MqttMsgPubrec.Parse(array[0], (byte)ProtocolVersion, channel);
							uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Frame, "RECV {0}", mqttMsgPubrec);
							EnqueueInternal(mqttMsgPubrec);
							break;
						}
						case 6:
						{
							MqttMsgPubrel mqttMsgPubrel = MqttMsgPubrel.Parse(array[0], (byte)ProtocolVersion, channel);
							uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Frame, "RECV {0}", mqttMsgPubrel);
							EnqueueInternal(mqttMsgPubrel);
							break;
						}
						case 7:
						{
							MqttMsgPubcomp mqttMsgPubcomp = MqttMsgPubcomp.Parse(array[0], (byte)ProtocolVersion, channel);
							uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Frame, "RECV {0}", mqttMsgPubcomp);
							EnqueueInternal(mqttMsgPubcomp);
							break;
						}
						case 10:
							throw new MqttClientException(MqttClientErrorCode.WrongBrokerMessage);
						case 11:
						{
							MqttMsgUnsuback mqttMsgUnsuback = MqttMsgUnsuback.Parse(array[0], (byte)ProtocolVersion, channel);
							uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Frame, "RECV {0}", mqttMsgUnsuback);
							EnqueueInternal(mqttMsgUnsuback);
							break;
						}
						case 14:
							throw new MqttClientException(MqttClientErrorCode.WrongBrokerMessage);
						default:
							throw new MqttClientException(MqttClientErrorCode.WrongBrokerMessage);
						}
						exReceiving = null;
					}
					else
					{
						OnConnectionClosing();
					}
				}
				catch (Exception ex)
				{
					uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Error, "Exception occurred: {0}", ex.ToString());
					exReceiving = new MqttCommunicationException(ex);
					bool flag = false;
					if (ex.GetType() == typeof(MqttClientException))
					{
						MqttClientException ex2 = ex as MqttClientException;
						flag = ex2.ErrorCode == MqttClientErrorCode.InvalidFlagBits || ex2.ErrorCode == MqttClientErrorCode.InvalidProtocolName || ex2.ErrorCode == MqttClientErrorCode.InvalidConnectFlags;
					}
					else if (ex.GetType() == typeof(IOException) || ex.GetType() == typeof(SocketException) || (ex.InnerException != null && ex.InnerException.GetType() == typeof(SocketException)))
					{
						flag = true;
					}
					if (flag)
					{
						OnConnectionClosing();
					}
				}
			}
		}

		private void KeepAliveThread()
		{
			int num = 0;
			int millisecondsTimeout = keepAlivePeriod;
			keepAliveEventEnd = new AutoResetEvent(initialState: false);
			while (isRunning)
			{
				keepAliveEvent.WaitOne(millisecondsTimeout);
				if (isRunning)
				{
					num = Environment.TickCount - lastCommTime;
					if (num >= keepAlivePeriod)
					{
						Ping();
						millisecondsTimeout = keepAlivePeriod;
					}
					else
					{
						millisecondsTimeout = keepAlivePeriod - num;
					}
				}
			}
			keepAliveEventEnd.Set();
		}

		private void DispatchEventThread()
		{
			while (isRunning)
			{
				if (eventQueue.Count == 0 && !isConnectionClosing)
				{
					receiveEventWaitHandle.WaitOne();
				}
				if (!isRunning)
				{
					continue;
				}
				InternalEvent internalEvent = null;
				lock (eventQueue)
				{
					if (eventQueue.Count > 0)
					{
						internalEvent = (InternalEvent)eventQueue.Dequeue();
					}
				}
				if (internalEvent != null)
				{
					MqttMsgBase message = ((MsgInternalEvent)internalEvent).Message;
					if (message != null)
					{
						switch (message.Type)
						{
						case 1:
							throw new MqttClientException(MqttClientErrorCode.WrongBrokerMessage);
						case 8:
							throw new MqttClientException(MqttClientErrorCode.WrongBrokerMessage);
						case 9:
							OnMqttMsgSubscribed((MqttMsgSuback)message);
							break;
						case 3:
							if (internalEvent.GetType() == typeof(MsgPublishedInternalEvent))
							{
								OnMqttMsgPublished(message.MessageId, isPublished: false);
							}
							else
							{
								OnMqttMsgPublishReceived((MqttMsgPublish)message);
							}
							break;
						case 4:
							OnMqttMsgPublished(message.MessageId, isPublished: true);
							break;
						case 6:
							OnMqttMsgPublishReceived((MqttMsgPublish)message);
							break;
						case 7:
							OnMqttMsgPublished(message.MessageId, isPublished: true);
							break;
						case 10:
							throw new MqttClientException(MqttClientErrorCode.WrongBrokerMessage);
						case 11:
							OnMqttMsgUnsubscribed(message.MessageId);
							break;
						case 14:
							throw new MqttClientException(MqttClientErrorCode.WrongBrokerMessage);
						}
					}
				}
				if (eventQueue.Count == 0 && isConnectionClosing)
				{
					Close();
					OnConnectionClosed();
				}
			}
		}

		private void ProcessInflightThread()
		{
			MqttMsgContext mqttMsgContext = null;
			MqttMsgBase mqttMsgBase = null;
			MqttMsgBase mqttMsgBase2 = null;
			InternalEvent internalEvent = null;
			bool flag = false;
			int num = -1;
			bool flag2 = false;
			try
			{
				while (isRunning)
				{
					inflightWaitHandle.WaitOne(num);
					if (!isRunning)
					{
						continue;
					}
					lock (inflightQueue)
					{
						flag2 = false;
						flag = false;
						mqttMsgBase2 = null;
						num = int.MaxValue;
						int num2 = inflightQueue.Count;
						while (num2 > 0)
						{
							num2--;
							flag = false;
							mqttMsgBase2 = null;
							if (!isRunning)
							{
								break;
							}
							mqttMsgContext = (MqttMsgContext)inflightQueue.Dequeue();
							mqttMsgBase = mqttMsgContext.Message;
							switch (mqttMsgContext.State)
							{
							case MqttMsgState.QueuedQos0:
								if (mqttMsgContext.Flow == MqttMsgFlow.ToPublish)
								{
									Send(mqttMsgBase);
								}
								else if (mqttMsgContext.Flow == MqttMsgFlow.ToAcknowledge)
								{
									internalEvent = new MsgInternalEvent(mqttMsgBase);
									OnInternalEvent(internalEvent);
								}
								uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Queuing, "processed {0}", mqttMsgBase);
								break;
							case MqttMsgState.QueuedQos1:
							case MqttMsgState.SendSubscribe:
							case MqttMsgState.SendUnsubscribe:
								if (mqttMsgContext.Flow == MqttMsgFlow.ToPublish)
								{
									mqttMsgContext.Timestamp = Environment.TickCount;
									mqttMsgContext.Attempt++;
									if (mqttMsgBase.Type == 3)
									{
										mqttMsgContext.State = MqttMsgState.WaitForPuback;
										if (mqttMsgContext.Attempt > 1)
										{
											mqttMsgBase.DupFlag = true;
										}
									}
									else if (mqttMsgBase.Type == 8)
									{
										mqttMsgContext.State = MqttMsgState.WaitForSuback;
									}
									else if (mqttMsgBase.Type == 10)
									{
										mqttMsgContext.State = MqttMsgState.WaitForUnsuback;
									}
									Send(mqttMsgBase);
									num = ((settings.DelayOnRetry < num) ? settings.DelayOnRetry : num);
									inflightQueue.Enqueue(mqttMsgContext);
								}
								else if (mqttMsgContext.Flow == MqttMsgFlow.ToAcknowledge)
								{
									MqttMsgPuback mqttMsgPuback = new MqttMsgPuback();
									mqttMsgPuback.MessageId = mqttMsgBase.MessageId;
									Send(mqttMsgPuback);
									internalEvent = new MsgInternalEvent(mqttMsgBase);
									OnInternalEvent(internalEvent);
									uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Queuing, "processed {0}", mqttMsgBase);
								}
								break;
							case MqttMsgState.QueuedQos2:
								if (mqttMsgContext.Flow == MqttMsgFlow.ToPublish)
								{
									mqttMsgContext.Timestamp = Environment.TickCount;
									mqttMsgContext.Attempt++;
									mqttMsgContext.State = MqttMsgState.WaitForPubrec;
									if (mqttMsgContext.Attempt > 1)
									{
										mqttMsgBase.DupFlag = true;
									}
									Send(mqttMsgBase);
									num = ((settings.DelayOnRetry < num) ? settings.DelayOnRetry : num);
									inflightQueue.Enqueue(mqttMsgContext);
								}
								else if (mqttMsgContext.Flow == MqttMsgFlow.ToAcknowledge)
								{
									MqttMsgPubrec mqttMsgPubrec = new MqttMsgPubrec();
									mqttMsgPubrec.MessageId = mqttMsgBase.MessageId;
									mqttMsgContext.State = MqttMsgState.WaitForPubrel;
									Send(mqttMsgPubrec);
									inflightQueue.Enqueue(mqttMsgContext);
								}
								break;
							case MqttMsgState.WaitForPuback:
							case MqttMsgState.WaitForSuback:
							case MqttMsgState.WaitForUnsuback:
							{
								if (mqttMsgContext.Flow != MqttMsgFlow.ToPublish)
								{
									break;
								}
								flag = false;
								lock (internalQueue)
								{
									if (internalQueue.Count > 0)
									{
										mqttMsgBase2 = (MqttMsgBase)internalQueue.Peek();
									}
								}
								if (mqttMsgBase2 != null && ((mqttMsgBase2.Type == 4 && mqttMsgBase.Type == 3 && mqttMsgBase2.MessageId == mqttMsgBase.MessageId) || (mqttMsgBase2.Type == 9 && mqttMsgBase.Type == 8 && mqttMsgBase2.MessageId == mqttMsgBase.MessageId) || (mqttMsgBase2.Type == 11 && mqttMsgBase.Type == 10 && mqttMsgBase2.MessageId == mqttMsgBase.MessageId)))
								{
									lock (internalQueue)
									{
										internalQueue.Dequeue();
										flag = true;
										flag2 = true;
										uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Queuing, "dequeued {0}", mqttMsgBase2);
									}
									internalEvent = ((mqttMsgBase2.Type != 4) ? new MsgInternalEvent(mqttMsgBase2) : new MsgPublishedInternalEvent(mqttMsgBase2, isPublished: true));
									OnInternalEvent(internalEvent);
									if (mqttMsgBase.Type == 3 && session != null && session.InflightMessages.ContainsKey(mqttMsgContext.Key))
									{
										session.InflightMessages.Remove(mqttMsgContext.Key);
									}
									uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Queuing, "processed {0}", mqttMsgBase);
								}
								if (flag)
								{
									break;
								}
								int num3 = Environment.TickCount - mqttMsgContext.Timestamp;
								if (num3 >= settings.DelayOnRetry)
								{
									if (mqttMsgContext.Attempt < settings.AttemptsOnRetry)
									{
										mqttMsgContext.State = MqttMsgState.QueuedQos1;
										inflightQueue.Enqueue(mqttMsgContext);
										num = 0;
									}
									else if (mqttMsgBase.Type == 3)
									{
										if (session != null && session.InflightMessages.ContainsKey(mqttMsgContext.Key))
										{
											session.InflightMessages.Remove(mqttMsgContext.Key);
										}
										internalEvent = new MsgPublishedInternalEvent(mqttMsgBase, isPublished: false);
										OnInternalEvent(internalEvent);
									}
								}
								else
								{
									inflightQueue.Enqueue(mqttMsgContext);
									int num6 = settings.DelayOnRetry - num3;
									num = ((num6 < num) ? num6 : num);
								}
								break;
							}
							case MqttMsgState.WaitForPubrec:
							{
								if (mqttMsgContext.Flow != MqttMsgFlow.ToPublish)
								{
									break;
								}
								flag = false;
								lock (internalQueue)
								{
									if (internalQueue.Count > 0)
									{
										mqttMsgBase2 = (MqttMsgBase)internalQueue.Peek();
									}
								}
								if (mqttMsgBase2 != null && mqttMsgBase2.Type == 5 && mqttMsgBase2.MessageId == mqttMsgBase.MessageId)
								{
									lock (internalQueue)
									{
										internalQueue.Dequeue();
										flag = true;
										flag2 = true;
										uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Queuing, "dequeued {0}", mqttMsgBase2);
									}
									MqttMsgPubrel mqttMsgPubrel2 = new MqttMsgPubrel();
									mqttMsgPubrel2.MessageId = mqttMsgBase.MessageId;
									mqttMsgContext.State = MqttMsgState.WaitForPubcomp;
									mqttMsgContext.Timestamp = Environment.TickCount;
									mqttMsgContext.Attempt = 1;
									Send(mqttMsgPubrel2);
									num = ((settings.DelayOnRetry < num) ? settings.DelayOnRetry : num);
									inflightQueue.Enqueue(mqttMsgContext);
								}
								if (flag)
								{
									break;
								}
								int num3 = Environment.TickCount - mqttMsgContext.Timestamp;
								if (num3 >= settings.DelayOnRetry)
								{
									if (mqttMsgContext.Attempt < settings.AttemptsOnRetry)
									{
										mqttMsgContext.State = MqttMsgState.QueuedQos2;
										inflightQueue.Enqueue(mqttMsgContext);
										num = 0;
										break;
									}
									if (session != null && session.InflightMessages.ContainsKey(mqttMsgContext.Key))
									{
										session.InflightMessages.Remove(mqttMsgContext.Key);
									}
									internalEvent = new MsgPublishedInternalEvent(mqttMsgBase, isPublished: false);
									OnInternalEvent(internalEvent);
								}
								else
								{
									inflightQueue.Enqueue(mqttMsgContext);
									int num5 = settings.DelayOnRetry - num3;
									num = ((num5 < num) ? num5 : num);
								}
								break;
							}
							case MqttMsgState.WaitForPubrel:
								if (mqttMsgContext.Flow != MqttMsgFlow.ToAcknowledge)
								{
									break;
								}
								lock (internalQueue)
								{
									if (internalQueue.Count > 0)
									{
										mqttMsgBase2 = (MqttMsgBase)internalQueue.Peek();
									}
								}
								if (mqttMsgBase2 != null && mqttMsgBase2.Type == 6)
								{
									if (mqttMsgBase2.MessageId == mqttMsgBase.MessageId)
									{
										lock (internalQueue)
										{
											internalQueue.Dequeue();
											flag2 = true;
											uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Queuing, "dequeued {0}", mqttMsgBase2);
										}
										MqttMsgPubcomp mqttMsgPubcomp = new MqttMsgPubcomp();
										mqttMsgPubcomp.MessageId = mqttMsgBase.MessageId;
										Send(mqttMsgPubcomp);
										internalEvent = new MsgInternalEvent(mqttMsgBase);
										OnInternalEvent(internalEvent);
										if (mqttMsgBase.Type == 3 && session != null && session.InflightMessages.ContainsKey(mqttMsgContext.Key))
										{
											session.InflightMessages.Remove(mqttMsgContext.Key);
										}
										uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Queuing, "processed {0}", mqttMsgBase);
									}
									else
									{
										inflightQueue.Enqueue(mqttMsgContext);
									}
								}
								else
								{
									inflightQueue.Enqueue(mqttMsgContext);
								}
								break;
							case MqttMsgState.WaitForPubcomp:
							{
								if (mqttMsgContext.Flow != MqttMsgFlow.ToPublish)
								{
									break;
								}
								flag = false;
								lock (internalQueue)
								{
									if (internalQueue.Count > 0)
									{
										mqttMsgBase2 = (MqttMsgBase)internalQueue.Peek();
									}
								}
								if (mqttMsgBase2 != null && mqttMsgBase2.Type == 7)
								{
									if (mqttMsgBase2.MessageId == mqttMsgBase.MessageId)
									{
										lock (internalQueue)
										{
											internalQueue.Dequeue();
											flag = true;
											flag2 = true;
											uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Queuing, "dequeued {0}", mqttMsgBase2);
										}
										internalEvent = new MsgPublishedInternalEvent(mqttMsgBase2, isPublished: true);
										OnInternalEvent(internalEvent);
										if (mqttMsgBase.Type == 3 && session != null && session.InflightMessages.ContainsKey(mqttMsgContext.Key))
										{
											session.InflightMessages.Remove(mqttMsgContext.Key);
										}
										uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Queuing, "processed {0}", mqttMsgBase);
									}
								}
								else if (mqttMsgBase2 != null && mqttMsgBase2.Type == 5 && mqttMsgBase2.MessageId == mqttMsgBase.MessageId)
								{
									lock (internalQueue)
									{
										internalQueue.Dequeue();
										flag = true;
										flag2 = true;
										uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Queuing, "dequeued {0}", mqttMsgBase2);
										inflightQueue.Enqueue(mqttMsgContext);
									}
								}
								if (flag)
								{
									break;
								}
								int num3 = Environment.TickCount - mqttMsgContext.Timestamp;
								if (num3 >= settings.DelayOnRetry)
								{
									if (mqttMsgContext.Attempt < settings.AttemptsOnRetry)
									{
										mqttMsgContext.State = MqttMsgState.SendPubrel;
										inflightQueue.Enqueue(mqttMsgContext);
										num = 0;
										break;
									}
									if (session != null && session.InflightMessages.ContainsKey(mqttMsgContext.Key))
									{
										session.InflightMessages.Remove(mqttMsgContext.Key);
									}
									internalEvent = new MsgPublishedInternalEvent(mqttMsgBase, isPublished: false);
									OnInternalEvent(internalEvent);
								}
								else
								{
									inflightQueue.Enqueue(mqttMsgContext);
									int num4 = settings.DelayOnRetry - num3;
									num = ((num4 < num) ? num4 : num);
								}
								break;
							}
							case MqttMsgState.SendPubrel:
								if (mqttMsgContext.Flow == MqttMsgFlow.ToPublish)
								{
									MqttMsgPubrel mqttMsgPubrel = new MqttMsgPubrel();
									mqttMsgPubrel.MessageId = mqttMsgBase.MessageId;
									mqttMsgContext.State = MqttMsgState.WaitForPubcomp;
									mqttMsgContext.Timestamp = Environment.TickCount;
									mqttMsgContext.Attempt++;
									if (ProtocolVersion == MqttProtocolVersion.Version_3_1 && mqttMsgContext.Attempt > 1)
									{
										mqttMsgPubrel.DupFlag = true;
									}
									Send(mqttMsgPubrel);
									num = ((settings.DelayOnRetry < num) ? settings.DelayOnRetry : num);
									inflightQueue.Enqueue(mqttMsgContext);
								}
								break;
							}
						}
						if (num == int.MaxValue)
						{
							num = -1;
						}
						if (mqttMsgBase2 != null && !flag2)
						{
							internalQueue.Dequeue();
							uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Queuing, "dequeued {0} orphan", mqttMsgBase2);
						}
					}
				}
			}
			catch (MqttCommunicationException ex)
			{
				if (mqttMsgContext != null)
				{
					inflightQueue.Enqueue(mqttMsgContext);
				}
				uPLibrary.Networking.M2Mqtt.Utility.Trace.WriteLine(uPLibrary.Networking.M2Mqtt.Utility.TraceLevel.Error, "Exception occurred: {0}", ex.ToString());
				OnConnectionClosing();
			}
		}

		private void RestoreSession()
		{
			if (!CleanSession)
			{
				if (session != null)
				{
					lock (inflightQueue)
					{
						foreach (MqttMsgContext value in session.InflightMessages.Values)
						{
							inflightQueue.Enqueue(value);
							if (value.Message.Type != 3 || value.Flow != MqttMsgFlow.ToPublish)
							{
								continue;
							}
							if (value.Message.QosLevel == 1 && value.State == MqttMsgState.WaitForPuback)
							{
								value.State = MqttMsgState.QueuedQos1;
							}
							else if (value.Message.QosLevel == 2)
							{
								if (value.State == MqttMsgState.WaitForPubrec)
								{
									value.State = MqttMsgState.QueuedQos2;
								}
								else if (value.State == MqttMsgState.WaitForPubcomp)
								{
									value.State = MqttMsgState.SendPubrel;
								}
							}
						}
					}
					inflightWaitHandle.Set();
				}
				else
				{
					session = new MqttClientSession(ClientId);
				}
			}
			else if (session != null)
			{
				session.Clear();
			}
		}

		private ushort GetMessageId()
		{
			messageIdCounter = (ushort)((messageIdCounter % 65535 == 0) ? 1 : ((ushort)(messageIdCounter + 1)));
			return messageIdCounter;
		}
	}
	public enum MqttProtocolVersion
	{
		Version_3_1 = 3,
		Version_3_1_1
	}
	public enum MqttSslProtocols
	{
		None,
		SSLv3,
		TLSv1_0,
		TLSv1_1,
		TLSv1_2
	}
	public class Fx
	{
		public static void StartThread(ThreadStart threadStart)
		{
			new Thread(threadStart).Start();
		}

		public static void SleepThread(int millisecondsTimeout)
		{
			Thread.Sleep(millisecondsTimeout);
		}
	}
	public class MqttNetworkChannel : IMqttNetworkChannel
	{
		private readonly RemoteCertificateValidationCallback userCertificateValidationCallback;

		private readonly LocalCertificateSelectionCallback userCertificateSelectionCallback;

		private string remoteHostName;

		private IPAddress remoteIpAddress;

		private int remotePort;

		private Socket socket;

		private bool secure;

		private X509Certificate caCert;

		private X509Certificate serverCert;

		private X509Certificate clientCert;

		private MqttSslProtocols sslProtocol;

		private SslStream sslStream;

		private NetworkStream netStream;

		public string RemoteHostName => remoteHostName;

		public IPAddress RemoteIpAddress => remoteIpAddress;

		public int RemotePort => remotePort;

		public bool DataAvailable
		{
			get
			{
				if (secure)
				{
					return netStream.DataAvailable;
				}
				return socket.Available > 0;
			}
		}

		public MqttNetworkChannel(Socket socket)
			: this(socket, secure: false, null, MqttSslProtocols.None, null, null)
		{
		}

		public MqttNetworkChannel(Socket socket, bool secure, X509Certificate serverCert, MqttSslProtocols sslProtocol, RemoteCertificateValidationCallback userCertificateValidationCallback, LocalCertificateSelectionCallback userCertificateSelectionCallback)
		{
			this.socket = socket;
			this.secure = secure;
			this.serverCert = serverCert;
			this.sslProtocol = sslProtocol;
			this.userCertificateValidationCallback = userCertificateValidationCallback;
			this.userCertificateSelectionCallback = userCertificateSelectionCallback;
		}

		public MqttNetworkChannel(string remoteHostName, int remotePort)
			: this(remoteHostName, remotePort, secure: false, null, null, MqttSslProtocols.None, null, null)
		{
		}

		public MqttNetworkChannel(string remoteHostName, int remotePort, bool secure, X509Certificate caCert, X509Certificate clientCert, MqttSslProtocols sslProtocol, RemoteCertificateValidationCallback userCertificateValidationCallback, LocalCertificateSelectionCallback userCertificateSelectionCallback)
		{
			this.remoteHostName = remoteHostName;
			remoteIpAddress = LookupRemoteIpAddress(remoteHostName);
			this.remotePort = remotePort;
			this.secure = secure;
			this.caCert = caCert;
			this.clientCert = clientCert;
			this.sslProtocol = sslProtocol;
			this.userCertificateValidationCallback = userCertificateValidationCallback;
			this.userCertificateSelectionCallback = userCertificateSelectionCallback;
		}

		private IPAddress LookupRemoteIpAddress(string remoteHostName)
		{
			IPAddress iPAddress = null;
			try
			{
				iPAddress = IPAddress.Parse(remoteHostName);
			}
			catch
			{
			}
			if (iPAddress == null)
			{
				IPHostEntry hostEntry = Dns.GetHostEntry(remoteHostName);
				if (hostEntry == null || hostEntry.AddressList.Length == 0)
				{
					throw new Exception("No address found for the remote host name");
				}
				int i;
				for (i = 0; hostEntry.AddressList[i] == null; i++)
				{
				}
				iPAddress = hostEntry.AddressList[i];
			}
			return iPAddress;
		}

		public void Connect()
		{
			remoteIpAddress = LookupRemoteIpAddress(remoteHostName);
			socket = new Socket(remoteIpAddress.GetAddressFamily(), SocketType.Stream, ProtocolType.Tcp);
			socket.Connect(new IPEndPoint(remoteIpAddress, remotePort));
			if (secure)
			{
				netStream = new NetworkStream(socket);
				sslStream = new SslStream(netStream, leaveInnerStreamOpen: false, userCertificateValidationCallback, userCertificateSelectionCallback);
				X509CertificateCollection clientCertificates = null;
				if (clientCert != null)
				{
					clientCertificates = new X509CertificateCollection(new X509Certificate[1] { clientCert });
				}
				sslStream.AuthenticateAsClient(remoteHostName, clientCertificates, MqttSslUtility.ToSslPlatformEnum(sslProtocol), checkCertificateRevocation: false);
			}
		}

		public int Send(byte[] buffer)
		{
			if (secure)
			{
				sslStream.Write(buffer, 0, buffer.Length);
				sslStream.Flush();
				return buffer.Length;
			}
			return socket.Send(buffer, 0, buffer.Length, SocketFlags.None);
		}

		public int Receive(byte[] buffer)
		{
			if (secure)
			{
				int i = 0;
				int num = 0;
				for (; i < buffer.Length; i += num)
				{
					num = sslStream.Read(buffer, i, buffer.Length - i);
					if (num == 0)
					{
						return 0;
					}
				}
				return buffer.Length;
			}
			int j = 0;
			int num2 = 0;
			for (; j < buffer.Length; j += num2)
			{
				num2 = socket.Receive(buffer, j, buffer.Length - j, SocketFlags.None);
				if (num2 == 0)
				{
					return 0;
				}
			}
			return buffer.Length;
		}

		public int Receive(byte[] buffer, int timeout)
		{
			if (socket.Poll(timeout * 1000, SelectMode.SelectRead))
			{
				return Receive(buffer);
			}
			return 0;
		}

		public void Close()
		{
			if (secure)
			{
				netStream.Close();
				sslStream.Close();
			}
			socket.Close();
		}

		public void Accept()
		{
			if (secure)
			{
				netStream = new NetworkStream(socket);
				sslStream = new SslStream(netStream, leaveInnerStreamOpen: false, userCertificateValidationCallback, userCertificateSelectionCallback);
				sslStream.AuthenticateAsServer(serverCert, clientCertificateRequired: false, MqttSslUtility.ToSslPlatformEnum(sslProtocol), checkCertificateRevocation: false);
			}
		}
	}
	public static class IPAddressUtility
	{
		public static AddressFamily GetAddressFamily(this IPAddress ipAddress)
		{
			return ipAddress.AddressFamily;
		}
	}
	public static class MqttSslUtility
	{
		public static SslProtocols ToSslPlatformEnum(MqttSslProtocols mqttSslProtocol)
		{
			return mqttSslProtocol switch
			{
				MqttSslProtocols.None => SslProtocols.None, 
				MqttSslProtocols.SSLv3 => SslProtocols.Ssl3, 
				MqttSslProtocols.TLSv1_0 => SslProtocols.Tls, 
				MqttSslProtocols.TLSv1_1 => SslProtocols.Tls11, 
				MqttSslProtocols.TLSv1_2 => SslProtocols.Tls12, 
				_ => throw new ArgumentException("SSL/TLS protocol version not supported"), 
			};
		}
	}
	public class MqttSettings
	{
		public const int MQTT_BROKER_DEFAULT_PORT = 1883;

		public const int MQTT_BROKER_DEFAULT_SSL_PORT = 8883;

		public const int MQTT_DEFAULT_TIMEOUT = 30000;

		public const int MQTT_ATTEMPTS_RETRY = 3;

		public const int MQTT_DELAY_RETRY = 10000;

		public const int MQTT_CONNECT_TIMEOUT = 30000;

		public const int MQTT_MAX_INFLIGHT_QUEUE_SIZE = int.MaxValue;

		private static MqttSettings instance;

		public int Port { get; internal set; }

		public int SslPort { get; internal set; }

		public int TimeoutOnConnection { get; internal set; }

		public int TimeoutOnReceiving { get; internal set; }

		public int AttemptsOnRetry { get; internal set; }

		public int DelayOnRetry { get; internal set; }

		public int InflightQueueSize { get; set; }

		public static MqttSettings Instance
		{
			get
			{
				if (instance == null)
				{
					instance = new MqttSettings();
				}
				return instance;
			}
		}

		private MqttSettings()
		{
			Port = 1883;
			SslPort = 8883;
			TimeoutOnReceiving = 30000;
			AttemptsOnRetry = 3;
			DelayOnRetry = 10000;
			TimeoutOnConnection = 30000;
			InflightQueueSize = int.MaxValue;
		}
	}
}
namespace uPLibrary.Networking.M2Mqtt.Utility
{
	public enum TraceLevel
	{
		Error = 1,
		Warning = 2,
		Information = 4,
		Verbose = 15,
		Frame = 16,
		Queuing = 32
	}
	public delegate void WriteTrace(string format, params object[] args);
	public static class Trace
	{
		public static TraceLevel TraceLevel;

		public static WriteTrace TraceListener;

		[Conditional("DEBUG")]
		public static void Debug(string format, params object[] args)
		{
			if (TraceListener != null)
			{
				TraceListener(format, args);
			}
		}

		public static void WriteLine(TraceLevel level, string format)
		{
			if (TraceListener != null && (level & TraceLevel) > (TraceLevel)0)
			{
				TraceListener(format);
			}
		}

		public static void WriteLine(TraceLevel level, string format, object arg1)
		{
			if (TraceListener != null && (level & TraceLevel) > (TraceLevel)0)
			{
				TraceListener(format, arg1);
			}
		}

		public static void WriteLine(TraceLevel level, string format, object arg1, object arg2)
		{
			if (TraceListener != null && (level & TraceLevel) > (TraceLevel)0)
			{
				TraceListener(format, arg1, arg2);
			}
		}

		public static void WriteLine(TraceLevel level, string format, object arg1, object arg2, object arg3)
		{
			if (TraceListener != null && (level & TraceLevel) > (TraceLevel)0)
			{
				TraceListener(format, arg1, arg2, arg3);
			}
		}
	}
	internal static class QueueExtension
	{
		internal delegate bool QueuePredicate(object item);

		internal static object Get(this Queue queue, QueuePredicate predicate)
		{
			foreach (object item in queue)
			{
				if (predicate(item))
				{
					return item;
				}
			}
			return null;
		}
	}
}
namespace uPLibrary.Networking.M2Mqtt.Session
{
	public class MqttClientSession : MqttSession
	{
		public MqttClientSession(string clientId)
			: base(clientId)
		{
		}
	}
	public abstract class MqttSession
	{
		public string ClientId { get; set; }

		public Hashtable InflightMessages { get; set; }

		public MqttSession()
			: this(null)
		{
		}

		public MqttSession(string clientId)
		{
			ClientId = clientId;
			InflightMessages = new Hashtable();
		}

		public virtual void Clear()
		{
			ClientId = null;
			InflightMessages.Clear();
		}
	}
}
namespace uPLibrary.Networking.M2Mqtt.Messages
{
	public abstract class MqttMsgBase
	{
		internal const byte MSG_TYPE_MASK = 240;

		internal const byte MSG_TYPE_OFFSET = 4;

		internal const byte MSG_TYPE_SIZE = 4;

		internal const byte MSG_FLAG_BITS_MASK = 15;

		internal const byte MSG_FLAG_BITS_OFFSET = 0;

		internal const byte MSG_FLAG_BITS_SIZE = 4;

		internal const byte DUP_FLAG_MASK = 8;

		internal const byte DUP_FLAG_OFFSET = 3;

		internal const byte DUP_FLAG_SIZE = 1;

		internal const byte QOS_LEVEL_MASK = 6;

		internal const byte QOS_LEVEL_OFFSET = 1;

		internal const byte QOS_LEVEL_SIZE = 2;

		internal const byte RETAIN_FLAG_MASK = 1;

		internal const byte RETAIN_FLAG_OFFSET = 0;

		internal const byte RETAIN_FLAG_SIZE = 1;

		internal const byte MQTT_MSG_CONNECT_TYPE = 1;

		internal const byte MQTT_MSG_CONNACK_TYPE = 2;

		internal const byte MQTT_MSG_PUBLISH_TYPE = 3;

		internal const byte MQTT_MSG_PUBACK_TYPE = 4;

		internal const byte MQTT_MSG_PUBREC_TYPE = 5;

		internal const byte MQTT_MSG_PUBREL_TYPE = 6;

		internal const byte MQTT_MSG_PUBCOMP_TYPE = 7;

		internal const byte MQTT_MSG_SUBSCRIBE_TYPE = 8;

		internal const byte MQTT_MSG_SUBACK_TYPE = 9;

		internal const byte MQTT_MSG_UNSUBSCRIBE_TYPE = 10;

		internal const byte MQTT_MSG_UNSUBACK_TYPE = 11;

		internal const byte MQTT_MSG_PINGREQ_TYPE = 12;

		internal const byte MQTT_MSG_PINGRESP_TYPE = 13;

		internal const byte MQTT_MSG_DISCONNECT_TYPE = 14;

		internal const byte MQTT_MSG_CONNECT_FLAG_BITS = 0;

		internal const byte MQTT_MSG_CONNACK_FLAG_BITS = 0;

		internal const byte MQTT_MSG_PUBLISH_FLAG_BITS = 0;

		internal const byte MQTT_MSG_PUBACK_FLAG_BITS = 0;

		internal const byte MQTT_MSG_PUBREC_FLAG_BITS = 0;

		internal const byte MQTT_MSG_PUBREL_FLAG_BITS = 2;

		internal const byte MQTT_MSG_PUBCOMP_FLAG_BITS = 0;

		internal const byte MQTT_MSG_SUBSCRIBE_FLAG_BITS = 2;

		internal const byte MQTT_MSG_SUBACK_FLAG_BITS = 0;

		internal const byte MQTT_MSG_UNSUBSCRIBE_FLAG_BITS = 2;

		internal const byte MQTT_MSG_UNSUBACK_FLAG_BITS = 0;

		internal const byte MQTT_MSG_PINGREQ_FLAG_BITS = 0;

		internal const byte MQTT_MSG_PINGRESP_FLAG_BITS = 0;

		internal const byte MQTT_MSG_DISCONNECT_FLAG_BITS = 0;

		public const byte QOS_LEVEL_AT_MOST_ONCE = 0;

		public const byte QOS_LEVEL_AT_LEAST_ONCE = 1;

		public const byte QOS_LEVEL_EXACTLY_ONCE = 2;

		public const byte QOS_LEVEL_GRANTED_FAILURE = 128;

		internal const ushort MAX_TOPIC_LENGTH = ushort.MaxValue;

		internal const ushort MIN_TOPIC_LENGTH = 1;

		internal const byte MESSAGE_ID_SIZE = 2;

		protected byte type;

		protected bool dupFlag;

		protected byte qosLevel;

		protected bool retain;

		protected ushort messageId;

		public byte Type
		{
			get
			{
				return type;
			}
			set
			{
				type = value;
			}
		}

		public bool DupFlag
		{
			get
			{
				return dupFlag;
			}
			set
			{
				dupFlag = value;
			}
		}

		public byte QosLevel
		{
			get
			{
				return qosLevel;
			}
			set
			{
				qosLevel = value;
			}
		}

		public bool Retain
		{
			get
			{
				return retain;
			}
			set
			{
				retain = value;
			}
		}

		public ushort MessageId
		{
			get
			{
				return messageId;
			}
			set
			{
				messageId = value;
			}
		}

		public abstract byte[] GetBytes(byte protocolVersion);

		protected int encodeRemainingLength(int remainingLength, byte[] buffer, int index)
		{
			int num = 0;
			do
			{
				num = remainingLength % 128;
				remainingLength /= 128;
				if (remainingLength > 0)
				{
					num |= 0x80;
				}
				buffer[index++] = (byte)num;
			}
			while (remainingLength > 0);
			return index;
		}

		protected static int decodeRemainingLength(IMqttNetworkChannel channel)
		{
			int num = 1;
			int num2 = 0;
			int num3 = 0;
			byte[] array = new byte[1];
			do
			{
				channel.Receive(array);
				num3 = array[0];
				num2 += (num3 & 0x7F) * num;
				num *= 128;
			}
			while ((num3 & 0x80) != 0);
			return num2;
		}

		protected string GetTraceString(string name, object[] fieldNames, object[] fieldValues)
		{
			StringBuilder stringBuilder = new StringBuilder();
			stringBuilder.Append(name);
			if (fieldNames != null && fieldValues != null)
			{
				stringBuilder.Append("(");
				bool flag = false;
				for (int i = 0; i < fieldValues.Length; i++)
				{
					if (fieldValues[i] != null)
					{
						if (flag)
						{
							stringBuilder.Append(",");
						}
						stringBuilder.Append(fieldNames[i]);
						stringBuilder.Append(":");
						stringBuilder.Append(GetStringObject(fieldValues[i]));
						flag = true;
					}
				}
				stringBuilder.Append(")");
			}
			return stringBuilder.ToString();
		}

		private object GetStringObject(object value)
		{
			if (value is byte[] array)
			{
				string text = "0123456789ABCDEF";
				StringBuilder stringBuilder = new StringBuilder(array.Length * 2);
				for (int i = 0; i < array.Length; i++)
				{
					stringBuilder.Append(text[array[i] >> 4]);
					stringBuilder.Append(text[array[i] & 0xF]);
				}
				return stringBuilder.ToString();
			}
			if (value is object[] array2)
			{
				StringBuilder stringBuilder2 = new StringBuilder();
				stringBuilder2.Append('[');
				for (int j = 0; j < array2.Length; j++)
				{
					if (j > 0)
					{
						stringBuilder2.Append(',');
					}
					stringBuilder2.Append(array2[j]);
				}
				stringBuilder2.Append(']');
				return stringBuilder2.ToString();
			}
			return value;
		}
	}
	public class MqttMsgConnack : MqttMsgBase
	{
		public const byte CONN_ACCEPTED = 0;

		public const byte CONN_REFUSED_PROT_VERS = 1;

		public const byte CONN_REFUSED_IDENT_REJECTED = 2;

		public const byte CONN_REFUSED_SERVER_UNAVAILABLE = 3;

		public const byte CONN_REFUSED_USERNAME_PASSWORD = 4;

		public const byte CONN_REFUSED_NOT_AUTHORIZED = 5;

		private const byte TOPIC_NAME_COMP_RESP_BYTE_OFFSET = 0;

		private const byte TOPIC_NAME_COMP_RESP_BYTE_SIZE = 1;

		private const byte CONN_ACK_FLAGS_BYTE_OFFSET = 0;

		private const byte CONN_ACK_FLAGS_BYTE_SIZE = 1;

		private const byte SESSION_PRESENT_FLAG_MASK = 1;

		private const byte SESSION_PRESENT_FLAG_OFFSET = 0;

		private const byte SESSION_PRESENT_FLAG_SIZE = 1;

		private const byte CONN_RETURN_CODE_BYTE_OFFSET = 1;

		private const byte CONN_RETURN_CODE_BYTE_SIZE = 1;

		private bool sessionPresent;

		private byte returnCode;

		public bool SessionPresent
		{
			get
			{
				return sessionPresent;
			}
			set
			{
				sessionPresent = value;
			}
		}

		public byte ReturnCode
		{
			get
			{
				return returnCode;
			}
			set
			{
				returnCode = value;
			}
		}

		public MqttMsgConnack()
		{
			type = 2;
		}

		public static MqttMsgConnack Parse(byte fixedHeaderFirstByte, byte protocolVersion, IMqttNetworkChannel channel)
		{
			MqttMsgConnack mqttMsgConnack = new MqttMsgConnack();
			if (protocolVersion == 4 && (fixedHeaderFirstByte & 0xF) != 0)
			{
				throw new MqttClientException(MqttClientErrorCode.InvalidFlagBits);
			}
			byte[] array = new byte[MqttMsgBase.decodeRemainingLength(channel)];
			channel.Receive(array);
			if (protocolVersion == 4)
			{
				mqttMsgConnack.sessionPresent = (array[0] & 1) != 0;
			}
			mqttMsgConnack.returnCode = array[1];
			return mqttMsgConnack;
		}

		public override byte[] GetBytes(byte ProtocolVersion)
		{
			int num = 0;
			int num2 = 0;
			int num3 = 0;
			int num4 = 0;
			int index = 0;
			num2 = ((ProtocolVersion != 4) ? (num2 + 2) : (num2 + 2));
			num4 += num2 + num3;
			num = 1;
			int num5 = num4;
			do
			{
				num++;
				num5 /= 128;
			}
			while (num5 > 0);
			byte[] array = new byte[num + num2 + num3];
			if (ProtocolVersion == 4)
			{
				array[index++] = 32;
			}
			else
			{
				array[index++] = 32;
			}
			index = encodeRemainingLength(num4, array, index);
			if (ProtocolVersion == 4)
			{
				array[index++] = (byte)(sessionPresent ? 1 : 0);
			}
			else
			{
				array[index++] = 0;
			}
			array[index++] = returnCode;
			return array;
		}

		public override string ToString()
		{
			return GetTraceString("CONNACK", new object[1] { "returnCode" }, new object[1] { returnCode });
		}
	}
	public class MqttMsgConnect : MqttMsgBase
	{
		internal const string PROTOCOL_NAME_V3_1 = "MQIsdp";

		internal const string PROTOCOL_NAME_V3_1_1 = "MQTT";

		internal const int CLIENT_ID_MAX_LENGTH = 23;

		internal const byte PROTOCOL_NAME_LEN_SIZE = 2;

		internal const byte PROTOCOL_NAME_V3_1_SIZE = 6;

		internal const byte PROTOCOL_NAME_V3_1_1_SIZE = 4;

		internal const byte PROTOCOL_VERSION_SIZE = 1;

		internal const byte CONNECT_FLAGS_SIZE = 1;

		internal const byte KEEP_ALIVE_TIME_SIZE = 2;

		internal const byte PROTOCOL_VERSION_V3_1 = 3;

		internal const byte PROTOCOL_VERSION_V3_1_1 = 4;

		internal const ushort KEEP_ALIVE_PERIOD_DEFAULT = 60;

		internal const ushort MAX_KEEP_ALIVE = ushort.MaxValue;

		internal const byte USERNAME_FLAG_MASK = 128;

		internal const byte USERNAME_FLAG_OFFSET = 7;

		internal const byte USERNAME_FLAG_SIZE = 1;

		internal const byte PASSWORD_FLAG_MASK = 64;

		internal const byte PASSWORD_FLAG_OFFSET = 6;

		internal const byte PASSWORD_FLAG_SIZE = 1;

		internal const byte WILL_RETAIN_FLAG_MASK = 32;

		internal const byte WILL_RETAIN_FLAG_OFFSET = 5;

		internal const byte WILL_RETAIN_FLAG_SIZE = 1;

		internal const byte WILL_QOS_FLAG_MASK = 24;

		internal const byte WILL_QOS_FLAG_OFFSET = 3;

		internal const byte WILL_QOS_FLAG_SIZE = 2;

		internal const byte WILL_FLAG_MASK = 4;

		internal const byte WILL_FLAG_OFFSET = 2;

		internal const byte WILL_FLAG_SIZE = 1;

		internal const byte CLEAN_SESSION_FLAG_MASK = 2;

		internal const byte CLEAN_SESSION_FLAG_OFFSET = 1;

		internal const byte CLEAN_SESSION_FLAG_SIZE = 1;

		internal const byte RESERVED_FLAG_MASK = 1;

		internal const byte RESERVED_FLAG_OFFSET = 0;

		internal const byte RESERVED_FLAG_SIZE = 1;

		private string protocolName;

		private byte protocolVersion;

		private string clientId;

		protected bool willRetain;

		protected byte willQosLevel;

		private bool willFlag;

		private string willTopic;

		private string willMessage;

		private string username;

		private string password;

		private bool cleanSession;

		private ushort keepAlivePeriod;

		public string ProtocolName
		{
			get
			{
				return protocolName;
			}
			set
			{
				protocolName = value;
			}
		}

		public byte ProtocolVersion
		{
			get
			{
				return protocolVersion;
			}
			set
			{
				protocolVersion = value;
			}
		}

		public string ClientId
		{
			get
			{
				return clientId;
			}
			set
			{
				clientId = value;
			}
		}

		public bool WillRetain
		{
			get
			{
				return willRetain;
			}
			set
			{
				willRetain = value;
			}
		}

		public byte WillQosLevel
		{
			get
			{
				return willQosLevel;
			}
			set
			{
				willQosLevel = value;
			}
		}

		public bool WillFlag
		{
			get
			{
				return willFlag;
			}
			set
			{
				willFlag = value;
			}
		}

		public string WillTopic
		{
			get
			{
				return willTopic;
			}
			set
			{
				willTopic = value;
			}
		}

		public string WillMessage
		{
			get
			{
				return willMessage;
			}
			set
			{
				willMessage = value;
			}
		}

		public string Username
		{
			get
			{
				return username;
			}
			set
			{
				username = value;
			}
		}

		public string Password
		{
			get
			{
				return password;
			}
			set
			{
				password = value;
			}
		}

		public bool CleanSession
		{
			get
			{
				return cleanSession;
			}
			set
			{
				cleanSession = value;
			}
		}

		public ushort KeepAlivePeriod
		{
			get
			{
				return keepAlivePeriod;
			}
			set
			{
				keepAlivePeriod = value;
			}
		}

		public MqttMsgConnect()
		{
			type = 1;
		}

		public MqttMsgConnect(string clientId)
			: this(clientId, null, null, willRetain: false, 1, willFlag: false, null, null, cleanSession: true, 60, 4)
		{
		}

		public MqttMsgConnect(string clientId, string username, string password, bool willRetain, byte willQosLevel, bool willFlag, string willTopic, string willMessage, bool cleanSession, ushort keepAlivePeriod, byte protocolVersion)
		{
			type = 1;
			this.clientId = clientId;
			this.username = username;
			this.password = password;
			this.willRetain = willRetain;
			this.willQosLevel = willQosLevel;
			this.willFlag = willFlag;
			this.willTopic = willTopic;
			this.willMessage = willMessage;
			this.cleanSession = cleanSession;
			this.keepAlivePeriod = keepAlivePeriod;
			this.protocolVersion = protocolVersion;
			protocolName = ((this.protocolVersion == 4) ? "MQTT" : "MQIsdp");
		}

		public static MqttMsgConnect Parse(byte fixedHeaderFirstByte, byte protocolVersion, IMqttNetworkChannel channel)
		{
			int num = 0;
			MqttMsgConnect mqttMsgConnect = new MqttMsgConnect();
			byte[] array = new byte[MqttMsgBase.decodeRemainingLength(channel)];
			channel.Receive(array);
			int num2 = (array[num++] << 8) & 0xFF00;
			num2 |= array[num++];
			byte[] array2 = new byte[num2];
			Array.Copy(array, num, array2, 0, num2);
			num += num2;
			mqttMsgConnect.protocolName = new string(Encoding.UTF8.GetChars(array2));
			if (!mqttMsgConnect.protocolName.Equals("MQIsdp") && !mqttMsgConnect.protocolName.Equals("MQTT"))
			{
				throw new MqttClientException(MqttClientErrorCode.InvalidProtocolName);
			}
			mqttMsgConnect.protocolVersion = array[num];
			num++;
			if (mqttMsgConnect.protocolVersion == 4 && (array[num] & 1) != 0)
			{
				throw new MqttClientException(MqttClientErrorCode.InvalidConnectFlags);
			}
			bool num3 = (array[num] & 0x80) != 0;
			bool flag = (array[num] & 0x40) != 0;
			mqttMsgConnect.willRetain = (array[num] & 0x20) != 0;
			mqttMsgConnect.willQosLevel = (byte)((array[num] & 0x18) >> 3);
			mqttMsgConnect.willFlag = (array[num] & 4) != 0;
			mqttMsgConnect.cleanSession = (array[num] & 2) != 0;
			num++;
			mqttMsgConnect.keepAlivePeriod = (ushort)((array[num++] << 8) & 0xFF00);
			mqttMsgConnect.keepAlivePeriod |= array[num++];
			int num4 = (array[num++] << 8) & 0xFF00;
			num4 |= array[num++];
			byte[] array3 = new byte[num4];
			Array.Copy(array, num, array3, 0, num4);
			num += num4;
			mqttMsgConnect.clientId = new string(Encoding.UTF8.GetChars(array3));
			if (mqttMsgConnect.protocolVersion == 4 && num4 == 0 && !mqttMsgConnect.cleanSession)
			{
				throw new MqttClientException(MqttClientErrorCode.InvalidClientId);
			}
			if (mqttMsgConnect.willFlag)
			{
				int num5 = (array[num++] << 8) & 0xFF00;
				num5 |= array[num++];
				byte[] array4 = new byte[num5];
				Array.Copy(array, num, array4, 0, num5);
				num += num5;
				mqttMsgConnect.willTopic = new string(Encoding.UTF8.GetChars(array4));
				int num6 = (array[num++] << 8) & 0xFF00;
				num6 |= array[num++];
				byte[] array5 = new byte[num6];
				Array.Copy(array, num, array5, 0, num6);
				num += num6;
				mqttMsgConnect.willMessage = new string(Encoding.UTF8.GetChars(array5));
			}
			if (num3)
			{
				int num7 = (array[num++] << 8) & 0xFF00;
				num7 |= array[num++];
				byte[] array6 = new byte[num7];
				Array.Copy(array, num, array6, 0, num7);
				num += num7;
				mqttMsgConnect.username = new string(Encoding.UTF8.GetChars(array6));
			}
			if (flag)
			{
				int num8 = (array[num++] << 8) & 0xFF00;
				num8 |= array[num++];
				byte[] array7 = new byte[num8];
				Array.Copy(array, num, array7, 0, num8);
				num += num8;
				mqttMsgConnect.password = new string(Encoding.UTF8.GetChars(array7));
			}
			return mqttMsgConnect;
		}

		public override byte[] GetBytes(byte protocolVersion)
		{
			int num = 0;
			int num2 = 0;
			int num3 = 0;
			int num4 = 0;
			int index = 0;
			byte[] bytes = Encoding.UTF8.GetBytes(clientId);
			byte[] array = ((willFlag && willTopic != null) ? Encoding.UTF8.GetBytes(willTopic) : null);
			byte[] array2 = ((willFlag && willMessage != null) ? Encoding.UTF8.GetBytes(willMessage) : null);
			byte[] array3 = ((username != null && username.Length > 0) ? Encoding.UTF8.GetBytes(username) : null);
			byte[] array4 = ((password != null && password.Length > 0) ? Encoding.UTF8.GetBytes(password) : null);
			if (this.protocolVersion == 4)
			{
				if (willFlag && (willQosLevel >= 3 || array == null || array2 == null || (array != null && array.Length == 0) || (array2 != null && array2.Length == 0)))
				{
					throw new MqttClientException(MqttClientErrorCode.WillWrong);
				}
				if (!willFlag && (willRetain || array != null || array2 != null || (array != null && array.Length != 0) || (array2 != null && array2.Length != 0)))
				{
					throw new MqttClientException(MqttClientErrorCode.WillWrong);
				}
			}
			if (keepAlivePeriod > ushort.MaxValue)
			{
				throw new MqttClientException(MqttClientErrorCode.KeepAliveWrong);
			}
			if (willQosLevel < 0 || willQosLevel > 2)
			{
				throw new MqttClientException(MqttClientErrorCode.WillWrong);
			}
			num2 = ((this.protocolVersion != 3) ? (num2 + 6) : (num2 + 8));
			num2++;
			num2++;
			num2 += 2;
			num3 += bytes.Length + 2;
			num3 += ((array != null) ? (array.Length + 2) : 0);
			num3 += ((array2 != null) ? (array2.Length + 2) : 0);
			num3 += ((array3 != null) ? (array3.Length + 2) : 0);
			num3 += ((array4 != null) ? (array4.Length + 2) : 0);
			num4 += num2 + num3;
			num = 1;
			int num5 = num4;
			do
			{
				num++;
				num5 /= 128;
			}
			while (num5 > 0);
			byte[] array5 = new byte[num + num2 + num3];
			array5[index++] = 16;
			index = encodeRemainingLength(num4, array5, index);
			array5[index++] = 0;
			if (this.protocolVersion == 3)
			{
				array5[index++] = 6;
				Array.Copy(Encoding.UTF8.GetBytes("MQIsdp"), 0, array5, index, 6);
				index += 6;
				array5[index++] = 3;
			}
			else
			{
				array5[index++] = 4;
				Array.Copy(Encoding.UTF8.GetBytes("MQTT"), 0, array5, index, 4);
				index += 4;
				array5[index++] = 4;
			}
			byte b = 0;
			b = (byte)(b | ((array3 != null) ? 128 : 0));
			b = (byte)(b | ((array4 != null) ? 64 : 0));
			b = (byte)(b | (willRetain ? 32 : 0));
			if (willFlag)
			{
				b |= (byte)(willQosLevel << 3);
			}
			b = (byte)(b | (willFlag ? 4 : 0));
			b = (byte)(b | (cleanSession ? 2 : 0));
			array5[index++] = b;
			array5[index++] = (byte)((keepAlivePeriod >> 8) & 0xFF);
			array5[index++] = (byte)(keepAlivePeriod & 0xFF);
			array5[index++] = (byte)((bytes.Length >> 8) & 0xFF);
			array5[index++] = (byte)(bytes.Length & 0xFF);
			Array.Copy(bytes, 0, array5, index, bytes.Length);
			index += bytes.Length;
			if (willFlag && array != null)
			{
				array5[index++] = (byte)((array.Length >> 8) & 0xFF);
				array5[index++] = (byte)(array.Length & 0xFF);
				Array.Copy(array, 0, array5, index, array.Length);
				index += array.Length;
			}
			if (willFlag && array2 != null)
			{
				array5[index++] = (byte)((array2.Length >> 8) & 0xFF);
				array5[index++] = (byte)(array2.Length & 0xFF);
				Array.Copy(array2, 0, array5, index, array2.Length);
				index += array2.Length;
			}
			if (array3 != null)
			{
				array5[index++] = (byte)((array3.Length >> 8) & 0xFF);
				array5[index++] = (byte)(array3.Length & 0xFF);
				Array.Copy(array3, 0, array5, index, array3.Length);
				index += array3.Length;
			}
			if (array4 != null)
			{
				array5[index++] = (byte)((array4.Length >> 8) & 0xFF);
				array5[index++] = (byte)(array4.Length & 0xFF);
				Array.Copy(array4, 0, array5, index, array4.Length);
				index += array4.Length;
			}
			return array5;
		}

		public override string ToString()
		{
			return GetTraceString("CONNECT", new object[12]
			{
				"protocolName", "protocolVersion", "clientId", "willFlag", "willRetain", "willQosLevel", "willTopic", "willMessage", "username", "password",
				"cleanSession", "keepAlivePeriod"
			}, new object[12]
			{
				protocolName, protocolVersion, clientId, willFlag, willRetain, willQosLevel, willTopic, willMessage, username, password,
				cleanSession, keepAlivePeriod
			});
		}
	}
	public class MqttMsgConnectEventArgs : EventArgs
	{
		public MqttMsgConnect Message { get; private set; }

		public MqttMsgConnectEventArgs(MqttMsgConnect connect)
		{
			Message = connect;
		}
	}
	public class MqttMsgContext
	{
		public MqttMsgBase Message { get; set; }

		public MqttMsgState State { get; set; }

		public MqttMsgFlow Flow { get; set; }

		public int Timestamp { get; set; }

		public int Attempt { get; set; }

		public string Key => string.Concat(Flow, "_", Message.MessageId);
	}
	public enum MqttMsgFlow
	{
		ToPublish,
		ToAcknowledge
	}
	public enum MqttMsgState
	{
		QueuedQos0,
		QueuedQos1,
		QueuedQos2,
		WaitForPuback,
		WaitForPubrec,
		WaitForPubrel,
		WaitForPubcomp,
		SendPubrec,
		SendPubrel,
		SendPubcomp,
		SendPuback,
		SendSubscribe,
		SendUnsubscribe,
		WaitForSuback,
		WaitForUnsuback
	}
	public class MqttMsgDisconnect : MqttMsgBase
	{
		public MqttMsgDisconnect()
		{
			type = 14;
		}

		public static MqttMsgDisconnect Parse(byte fixedHeaderFirstByte, byte protocolVersion, IMqttNetworkChannel channel)
		{
			MqttMsgDisconnect result = new MqttMsgDisconnect();
			if (protocolVersion == 4 && (fixedHeaderFirstByte & 0xF) != 0)
			{
				throw new MqttClientException(MqttClientErrorCode.InvalidFlagBits);
			}
			MqttMsgBase.decodeRemainingLength(channel);
			return result;
		}

		public override byte[] GetBytes(byte protocolVersion)
		{
			byte[] array = new byte[2];
			int num = 0;
			if (protocolVersion == 4)
			{
				array[num++] = 224;
			}
			else
			{
				array[num++] = 224;
			}
			array[num++] = 0;
			return array;
		}

		public override string ToString()
		{
			return GetTraceString("DISCONNECT", null, null);
		}
	}
	public class MqttMsgPingReq : MqttMsgBase
	{
		public MqttMsgPingReq()
		{
			type = 12;
		}

		public override byte[] GetBytes(byte protocolVersion)
		{
			byte[] array = new byte[2];
			int num = 0;
			if (protocolVersion == 4)
			{
				array[num++] = 192;
			}
			else
			{
				array[num++] = 192;
			}
			array[num++] = 0;
			return array;
		}

		public static MqttMsgPingReq Parse(byte fixedHeaderFirstByte, byte protocolVersion, IMqttNetworkChannel channel)
		{
			MqttMsgPingReq result = new MqttMsgPingReq();
			if (protocolVersion == 4 && (fixedHeaderFirstByte & 0xF) != 0)
			{
				throw new MqttClientException(MqttClientErrorCode.InvalidFlagBits);
			}
			MqttMsgBase.decodeRemainingLength(channel);
			return result;
		}

		public override string ToString()
		{
			return GetTraceString("PINGREQ", null, null);
		}
	}
	public class MqttMsgPingResp : MqttMsgBase
	{
		public MqttMsgPingResp()
		{
			type = 13;
		}

		public static MqttMsgPingResp Parse(byte fixedHeaderFirstByte, byte protocolVersion, IMqttNetworkChannel channel)
		{
			MqttMsgPingResp result = new MqttMsgPingResp();
			if (protocolVersion == 4 && (fixedHeaderFirstByte & 0xF) != 0)
			{
				throw new MqttClientException(MqttClientErrorCode.InvalidFlagBits);
			}
			MqttMsgBase.decodeRemainingLength(channel);
			return result;
		}

		public override byte[] GetBytes(byte protocolVersion)
		{
			byte[] array = new byte[2];
			int num = 0;
			if (protocolVersion == 4)
			{
				array[num++] = 208;
			}
			else
			{
				array[num++] = 208;
			}
			array[num++] = 0;
			return array;
		}

		public override string ToString()
		{
			return GetTraceString("PINGRESP", null, null);
		}
	}
	public class MqttMsgPuback : MqttMsgBase
	{
		public MqttMsgPuback()
		{
			type = 4;
		}

		public override byte[] GetBytes(byte protocolVersion)
		{
			int num = 0;
			int num2 = 0;
			int num3 = 0;
			int num4 = 0;
			int index = 0;
			num2 += 2;
			num4 += num2 + num3;
			num = 1;
			int num5 = num4;
			do
			{
				num++;
				num5 /= 128;
			}
			while (num5 > 0);
			byte[] array = new byte[num + num2 + num3];
			if (protocolVersion == 4)
			{
				array[index++] = 64;
			}
			else
			{
				array[index++] = 64;
			}
			index = encodeRemainingLength(num4, array, index);
			array[index++] = (byte)((messageId >> 8) & 0xFF);
			array[index++] = (byte)(messageId & 0xFF);
			return array;
		}

		public static MqttMsgPuback Parse(byte fixedHeaderFirstByte, byte protocolVersion, IMqttNetworkChannel channel)
		{
			int num = 0;
			MqttMsgPuback mqttMsgPuback = new MqttMsgPuback();
			if (protocolVersion == 4 && (fixedHeaderFirstByte & 0xF) != 0)
			{
				throw new MqttClientException(MqttClientErrorCode.InvalidFlagBits);
			}
			byte[] array = new byte[MqttMsgBase.decodeRemainingLength(channel)];
			channel.Receive(array);
			mqttMsgPuback.messageId = (ushort)((array[num++] << 8) & 0xFF00);
			mqttMsgPuback.messageId |= array[num++];
			return mqttMsgPuback;
		}

		public override string ToString()
		{
			return GetTraceString("PUBACK", new object[1] { "messageId" }, new object[1] { messageId });
		}
	}
	public class MqttMsgPubcomp : MqttMsgBase
	{
		public MqttMsgPubcomp()
		{
			type = 7;
		}

		public override byte[] GetBytes(byte protocolVersion)
		{
			int num = 0;
			int num2 = 0;
			int num3 = 0;
			int num4 = 0;
			int index = 0;
			num2 += 2;
			num4 += num2 + num3;
			num = 1;
			int num5 = num4;
			do
			{
				num++;
				num5 /= 128;
			}
			while (num5 > 0);
			byte[] array = new byte[num + num2 + num3];
			if (protocolVersion == 4)
			{
				array[index++] = 112;
			}
			else
			{
				array[index++] = 112;
			}
			index = encodeRemainingLength(num4, array, index);
			array[index++] = (byte)((messageId >> 8) & 0xFF);
			array[index++] = (byte)(messageId & 0xFF);
			return array;
		}

		public static MqttMsgPubcomp Parse(byte fixedHeaderFirstByte, byte protocolVersion, IMqttNetworkChannel channel)
		{
			int num = 0;
			MqttMsgPubcomp mqttMsgPubcomp = new MqttMsgPubcomp();
			if (protocolVersion == 4 && (fixedHeaderFirstByte & 0xF) != 0)
			{
				throw new MqttClientException(MqttClientErrorCode.InvalidFlagBits);
			}
			byte[] array = new byte[MqttMsgBase.decodeRemainingLength(channel)];
			channel.Receive(array);
			mqttMsgPubcomp.messageId = (ushort)((array[num++] << 8) & 0xFF00);
			mqttMsgPubcomp.messageId |= array[num++];
			return mqttMsgPubcomp;
		}

		public override string ToString()
		{
			return GetTraceString("PUBCOMP", new object[1] { "messageId" }, new object[1] { messageId });
		}
	}
	public class MqttMsgPublish : MqttMsgBase
	{
		private string topic;

		private byte[] message;

		public string Topic
		{
			get
			{
				return topic;
			}
			set
			{
				topic = value;
			}
		}

		public byte[] Message
		{
			get
			{
				return message;
			}
			set
			{
				message = value;
			}
		}

		public MqttMsgPublish()
		{
			type = 3;
		}

		public MqttMsgPublish(string topic, byte[] message)
			: this(topic, message, dupFlag: false, 0, retain: false)
		{
		}

		public MqttMsgPublish(string topic, byte[] message, bool dupFlag, byte qosLevel, bool retain)
		{
			type = 3;
			this.topic = topic;
			this.message = message;
			base.dupFlag = dupFlag;
			base.qosLevel = qosLevel;
			base.retain = retain;
			messageId = 0;
		}

		public override byte[] GetBytes(byte protocolVersion)
		{
			int num = 0;
			int num2 = 0;
			int num3 = 0;
			int num4 = 0;
			int num5 = 0;
			if (topic.IndexOf('#') != -1 || topic.IndexOf('+') != -1)
			{
				throw new MqttClientException(MqttClientErrorCode.TopicWildcard);
			}
			if (topic.Length < 1 || topic.Length > 65535)
			{
				throw new MqttClientException(MqttClientErrorCode.TopicLength);
			}
			if (qosLevel > 2)
			{
				throw new MqttClientException(MqttClientErrorCode.QosNotAllowed);
			}
			byte[] bytes = Encoding.UTF8.GetBytes(topic);
			num2 += bytes.Length + 2;
			if (qosLevel == 1 || qosLevel == 2)
			{
				num2 += 2;
			}
			if (message != null)
			{
				num3 += message.Length;
			}
			num4 += num2 + num3;
			num = 1;
			int num6 = num4;
			do
			{
				num++;
				num6 /= 128;
			}
			while (num6 > 0);
			byte[] array = new byte[num + num2 + num3];
			array[num5] = (byte)(0x30 | (qosLevel << 1));
			array[num5] |= (byte)(dupFlag ? 8 : 0);
			array[num5] |= (byte)(retain ? 1 : 0);
			num5++;
			num5 = encodeRemainingLength(num4, array, num5);
			array[num5++] = (byte)((bytes.Length >> 8) & 0xFF);
			array[num5++] = (byte)(bytes.Length & 0xFF);
			Array.Copy(bytes, 0, array, num5, bytes.Length);
			num5 += bytes.Length;
			if (qosLevel == 1 || qosLevel == 2)
			{
				if (messageId == 0)
				{
					throw new MqttClientException(MqttClientErrorCode.WrongMessageId);
				}
				array[num5++] = (byte)((messageId >> 8) & 0xFF);
				array[num5++] = (byte)(messageId & 0xFF);
			}
			if (message != null)
			{
				Array.Copy(message, 0, array, num5, message.Length);
				num5 += message.Length;
			}
			return array;
		}

		public static MqttMsgPublish Parse(byte fixedHeaderFirstByte, byte protocolVersion, IMqttNetworkChannel channel)
		{
			int num = 0;
			MqttMsgPublish mqttMsgPublish = new MqttMsgPublish();
			int num2 = MqttMsgBase.decodeRemainingLength(channel);
			byte[] array = new byte[num2];
			int num3 = channel.Receive(array);
			int num4 = (array[num++] << 8) & 0xFF00;
			num4 |= array[num++];
			byte[] array2 = new byte[num4];
			Array.Copy(array, num, array2, 0, num4);
			num += num4;
			mqttMsgPublish.topic = new string(Encoding.UTF8.GetChars(array2));
			mqttMsgPublish.qosLevel = (byte)((fixedHeaderFirstByte & 6) >> 1);
			if (mqttMsgPublish.qosLevel > 2)
			{
				throw new MqttClientException(MqttClientErrorCode.QosNotAllowed);
			}
			mqttMsgPublish.dupFlag = (fixedHeaderFirstByte & 8) >> 3 == 1;
			mqttMsgPublish.retain = (fixedHeaderFirstByte & 1) == 1;
			if (mqttMsgPublish.qosLevel == 1 || mqttMsgPublish.qosLevel == 2)
			{
				mqttMsgPublish.messageId = (ushort)((array[num++] << 8) & 0xFF00);
				mqttMsgPublish.messageId |= array[num++];
			}
			int num5 = num2 - num;
			int num6 = num5;
			int num7 = 0;
			mqttMsgPublish.message = new byte[num5];
			Array.Copy(array, num, mqttMsgPublish.message, num7, num3 - num);
			num6 -= num3 - num;
			num7 += num3 - num;
			while (num6 > 0)
			{
				num3 = channel.Receive(array);
				Array.Copy(array, 0, mqttMsgPublish.message, num7, num3);
				num6 -= num3;
				num7 += num3;
			}
			return mqttMsgPublish;
		}

		public override string ToString()
		{
			return GetTraceString("PUBLISH", new object[3] { "messageId", "topic", "message" }, new object[3] { messageId, topic, message });
		}
	}
	public class MqttMsgPublishedEventArgs : EventArgs
	{
		private ushort messageId;

		private bool isPublished;

		public ushort MessageId
		{
			get
			{
				return messageId;
			}
			internal set
			{
				messageId = value;
			}
		}

		public bool IsPublished
		{
			get
			{
				return isPublished;
			}
			internal set
			{
				isPublished = value;
			}
		}

		public MqttMsgPublishedEventArgs(ushort messageId)
			: this(messageId, isPublished: true)
		{
		}

		public MqttMsgPublishedEventArgs(ushort messageId, bool isPublished)
		{
			this.messageId = messageId;
			this.isPublished = isPublished;
		}
	}
	public class MqttMsgPublishEventArgs : EventArgs
	{
		private string topic;

		private byte[] message;

		private bool dupFlag;

		private byte qosLevel;

		private bool retain;

		public string Topic
		{
			get
			{
				return topic;
			}
			internal set
			{
				topic = value;
			}
		}

		public byte[] Message
		{
			get
			{
				return message;
			}
			internal set
			{
				message = value;
			}
		}

		public bool DupFlag
		{
			get
			{
				return dupFlag;
			}
			set
			{
				dupFlag = value;
			}
		}

		public byte QosLevel
		{
			get
			{
				return qosLevel;
			}
			internal set
			{
				qosLevel = value;
			}
		}

		public bool Retain
		{
			get
			{
				return retain;
			}
			internal set
			{
				retain = value;
			}
		}

		public MqttMsgPublishEventArgs(string topic, byte[] message, bool dupFlag, byte qosLevel, bool retain)
		{
			this.topic = topic;
			this.message = message;
			this.dupFlag = dupFlag;
			this.qosLevel = qosLevel;
			this.retain = retain;
		}
	}
	public class MqttMsgPubrec : MqttMsgBase
	{
		public MqttMsgPubrec()
		{
			type = 5;
		}

		public override byte[] GetBytes(byte protocolVersion)
		{
			int num = 0;
			int num2 = 0;
			int num3 = 0;
			int num4 = 0;
			int index = 0;
			num2 += 2;
			num4 += num2 + num3;
			num = 1;
			int num5 = num4;
			do
			{
				num++;
				num5 /= 128;
			}
			while (num5 > 0);
			byte[] array = new byte[num + num2 + num3];
			if (protocolVersion == 4)
			{
				array[index++] = 80;
			}
			else
			{
				array[index++] = 80;
			}
			index = encodeRemainingLength(num4, array, index);
			array[index++] = (byte)((messageId >> 8) & 0xFF);
			array[index++] = (byte)(messageId & 0xFF);
			return array;
		}

		public static MqttMsgPubrec Parse(byte fixedHeaderFirstByte, byte protocolVersion, IMqttNetworkChannel channel)
		{
			int num = 0;
			MqttMsgPubrec mqttMsgPubrec = new MqttMsgPubrec();
			if (protocolVersion == 4 && (fixedHeaderFirstByte & 0xF) != 0)
			{
				throw new MqttClientException(MqttClientErrorCode.InvalidFlagBits);
			}
			byte[] array = new byte[MqttMsgBase.decodeRemainingLength(channel)];
			channel.Receive(array);
			mqttMsgPubrec.messageId = (ushort)((array[num++] << 8) & 0xFF00);
			mqttMsgPubrec.messageId |= array[num++];
			return mqttMsgPubrec;
		}

		public override string ToString()
		{
			return GetTraceString("PUBREC", new object[1] { "messageId" }, new object[1] { messageId });
		}
	}
	public class MqttMsgPubrel : MqttMsgBase
	{
		public MqttMsgPubrel()
		{
			type = 6;
			qosLevel = 1;
		}

		public override byte[] GetBytes(byte protocolVersion)
		{
			int num = 0;
			int num2 = 0;
			int num3 = 0;
			int num4 = 0;
			int num5 = 0;
			num2 += 2;
			num4 += num2 + num3;
			num = 1;
			int num6 = num4;
			do
			{
				num++;
				num6 /= 128;
			}
			while (num6 > 0);
			byte[] array = new byte[num + num2 + num3];
			if (protocolVersion == 4)
			{
				array[num5++] = 98;
			}
			else
			{
				array[num5] = (byte)(0x60 | (qosLevel << 1));
				array[num5] |= (byte)(dupFlag ? 8 : 0);
				num5++;
			}
			num5 = encodeRemainingLength(num4, array, num5);
			array[num5++] = (byte)((messageId >> 8) & 0xFF);
			array[num5++] = (byte)(messageId & 0xFF);
			return array;
		}

		public static MqttMsgPubrel Parse(byte fixedHeaderFirstByte, byte protocolVersion, IMqttNetworkChannel channel)
		{
			int num = 0;
			MqttMsgPubrel mqttMsgPubrel = new MqttMsgPubrel();
			if (protocolVersion == 4 && (fixedHeaderFirstByte & 0xF) != 2)
			{
				throw new MqttClientException(MqttClientErrorCode.InvalidFlagBits);
			}
			byte[] array = new byte[MqttMsgBase.decodeRemainingLength(channel)];
			channel.Receive(array);
			if (protocolVersion == 3)
			{
				mqttMsgPubrel.qosLevel = (byte)((fixedHeaderFirstByte & 6) >> 1);
				mqttMsgPubrel.dupFlag = (fixedHeaderFirstByte & 8) >> 3 == 1;
			}
			mqttMsgPubrel.messageId = (ushort)((array[num++] << 8) & 0xFF00);
			mqttMsgPubrel.messageId |= array[num++];
			return mqttMsgPubrel;
		}

		public override string ToString()
		{
			return GetTraceString("PUBREL", new object[1] { "messageId" }, new object[1] { messageId });
		}
	}
	public class MqttMsgSuback : MqttMsgBase
	{
		private byte[] grantedQosLevels;

		public byte[] GrantedQoSLevels
		{
			get
			{
				return grantedQosLevels;
			}
			set
			{
				grantedQosLevels = value;
			}
		}

		public MqttMsgSuback()
		{
			type = 9;
		}

		public static MqttMsgSuback Parse(byte fixedHeaderFirstByte, byte protocolVersion, IMqttNetworkChannel channel)
		{
			int num = 0;
			MqttMsgSuback mqttMsgSuback = new MqttMsgSuback();
			if (protocolVersion == 4 && (fixedHeaderFirstByte & 0xF) != 0)
			{
				throw new MqttClientException(MqttClientErrorCode.InvalidFlagBits);
			}
			int num2 = MqttMsgBase.decodeRemainingLength(channel);
			byte[] array = new byte[num2];
			channel.Receive(array);
			mqttMsgSuback.messageId = (ushort)((array[num++] << 8) & 0xFF00);
			mqttMsgSuback.messageId |= array[num++];
			mqttMsgSuback.grantedQosLevels = new byte[num2 - 2];
			int num3 = 0;
			do
			{
				mqttMsgSuback.grantedQosLevels[num3++] = array[num++];
			}
			while (num < num2);
			return mqttMsgSuback;
		}

		public override byte[] GetBytes(byte protocolVersion)
		{
			int num = 0;
			int num2 = 0;
			int num3 = 0;
			int num4 = 0;
			int index = 0;
			num2 += 2;
			int num5 = 0;
			for (num5 = 0; num5 < grantedQosLevels.Length; num5++)
			{
				num3++;
			}
			num4 += num2 + num3;
			num = 1;
			int num6 = num4;
			do
			{
				num++;
				num6 /= 128;
			}
			while (num6 > 0);
			byte[] array = new byte[num + num2 + num3];
			if (protocolVersion == 4)
			{
				array[index++] = 144;
			}
			else
			{
				array[index++] = 144;
			}
			index = encodeRemainingLength(num4, array, index);
			array[index++] = (byte)((messageId >> 8) & 0xFF);
			array[index++] = (byte)(messageId & 0xFF);
			for (num5 = 0; num5 < grantedQosLevels.Length; num5++)
			{
				array[index++] = grantedQosLevels[num5];
			}
			return array;
		}

		public override string ToString()
		{
			return GetTraceString("SUBACK", new object[2] { "messageId", "grantedQosLevels" }, new object[2] { messageId, grantedQosLevels });
		}
	}
	public class MqttMsgSubscribe : MqttMsgBase
	{
		private string[] topics;

		private byte[] qosLevels;

		public string[] Topics
		{
			get
			{
				return topics;
			}
			set
			{
				topics = value;
			}
		}

		public byte[] QoSLevels
		{
			get
			{
				return qosLevels;
			}
			set
			{
				qosLevels = value;
			}
		}

		public MqttMsgSubscribe()
		{
			type = 8;
		}

		public MqttMsgSubscribe(string[] topics, byte[] qosLevels)
		{
			type = 8;
			this.topics = topics;
			this.qosLevels = qosLevels;
			qosLevel = 1;
		}

		public static MqttMsgSubscribe Parse(byte fixedHeaderFirstByte, byte protocolVersion, IMqttNetworkChannel channel)
		{
			int num = 0;
			MqttMsgSubscribe mqttMsgSubscribe = new MqttMsgSubscribe();
			if (protocolVersion == 4 && (fixedHeaderFirstByte & 0xF) != 2)
			{
				throw new MqttClientException(MqttClientErrorCode.InvalidFlagBits);
			}
			int num2 = MqttMsgBase.decodeRemainingLength(channel);
			byte[] array = new byte[num2];
			channel.Receive(array);
			if (protocolVersion == 3)
			{
				mqttMsgSubscribe.qosLevel = (byte)((fixedHeaderFirstByte & 6) >> 1);
				mqttMsgSubscribe.dupFlag = (fixedHeaderFirstByte & 8) >> 3 == 1;
				mqttMsgSubscribe.retain = false;
			}
			mqttMsgSubscribe.messageId = (ushort)((array[num++] << 8) & 0xFF00);
			mqttMsgSubscribe.messageId |= array[num++];
			IList<string> list = new List<string>();
			IList<byte> list2 = new List<byte>();
			do
			{
				int num3 = (array[num++] << 8) & 0xFF00;
				num3 |= array[num++];
				byte[] array2 = new byte[num3];
				Array.Copy(array, num, array2, 0, num3);
				num += num3;
				list.Add(new string(Encoding.UTF8.GetChars(array2)));
				list2.Add(array[num++]);
			}
			while (num < num2);
			mqttMsgSubscribe.topics = new string[list.Count];
			mqttMsgSubscribe.qosLevels = new byte[list2.Count];
			for (int i = 0; i < list.Count; i++)
			{
				mqttMsgSubscribe.topics[i] = list[i];
				mqttMsgSubscribe.qosLevels[i] = list2[i];
			}
			return mqttMsgSubscribe;
		}

		public override byte[] GetBytes(byte protocolVersion)
		{
			int num = 0;
			int num2 = 0;
			int num3 = 0;
			int num4 = 0;
			int num5 = 0;
			if (topics == null || topics.Length == 0)
			{
				throw new MqttClientException(MqttClientErrorCode.TopicsEmpty);
			}
			if (qosLevels == null || qosLevels.Length == 0)
			{
				throw new MqttClientException(MqttClientErrorCode.QosLevelsEmpty);
			}
			if (topics.Length != qosLevels.Length)
			{
				throw new MqttClientException(MqttClientErrorCode.TopicsQosLevelsNotMatch);
			}
			num2 += 2;
			int num6 = 0;
			byte[][] array = new byte[topics.Length][];
			for (num6 = 0; num6 < topics.Length; num6++)
			{
				if (topics[num6].Length < 1 || topics[num6].Length > 65535)
				{
					throw new MqttClientException(MqttClientErrorCode.TopicLength);
				}
				array[num6] = Encoding.UTF8.GetBytes(topics[num6]);
				num3 += 2;
				num3 += array[num6].Length;
				num3++;
			}
			num4 += num2 + num3;
			num = 1;
			int num7 = num4;
			do
			{
				num++;
				num7 /= 128;
			}
			while (num7 > 0);
			byte[] array2 = new byte[num + num2 + num3];
			if (protocolVersion == 4)
			{
				array2[num5++] = 130;
			}
			else
			{
				array2[num5] = (byte)(0x80 | (qosLevel << 1));
				array2[num5] |= (byte)(dupFlag ? 8 : 0);
				num5++;
			}
			num5 = encodeRemainingLength(num4, array2, num5);
			if (messageId == 0)
			{
				throw new MqttClientException(MqttClientErrorCode.WrongMessageId);
			}
			array2[num5++] = (byte)((messageId >> 8) & 0xFF);
			array2[num5++] = (byte)(messageId & 0xFF);
			num6 = 0;
			for (num6 = 0; num6 < topics.Length; num6++)
			{
				array2[num5++] = (byte)((array[num6].Length >> 8) & 0xFF);
				array2[num5++] = (byte)(array[num6].Length & 0xFF);
				Array.Copy(array[num6], 0, array2, num5, array[num6].Length);
				num5 += array[num6].Length;
				array2[num5++] = qosLevels[num6];
			}
			return array2;
		}

		public override string ToString()
		{
			return GetTraceString("SUBSCRIBE", new object[3] { "messageId", "topics", "qosLevels" }, new object[3] { messageId, topics, qosLevels });
		}
	}
	public class MqttMsgSubscribedEventArgs : EventArgs
	{
		private ushort messageId;

		private byte[] grantedQosLevels;

		public ushort MessageId
		{
			get
			{
				return messageId;
			}
			internal set
			{
				messageId = value;
			}
		}

		public byte[] GrantedQoSLevels
		{
			get
			{
				return grantedQosLevels;
			}
			internal set
			{
				grantedQosLevels = value;
			}
		}

		public MqttMsgSubscribedEventArgs(ushort messageId, byte[] grantedQosLevels)
		{
			this.messageId = messageId;
			this.grantedQosLevels = grantedQosLevels;
		}
	}
	public class MqttMsgSubscribeEventArgs : EventArgs
	{
		private ushort messageId;

		private string[] topics;

		private byte[] qosLevels;

		public ushort MessageId
		{
			get
			{
				return messageId;
			}
			internal set
			{
				messageId = value;
			}
		}

		public string[] Topics
		{
			get
			{
				return topics;
			}
			internal set
			{
				topics = value;
			}
		}

		public byte[] QoSLevels
		{
			get
			{
				return qosLevels;
			}
			internal set
			{
				qosLevels = value;
			}
		}

		public MqttMsgSubscribeEventArgs(ushort messageId, string[] topics, byte[] qosLevels)
		{
			this.messageId = messageId;
			this.topics = topics;
			this.qosLevels = qosLevels;
		}
	}
	public class MqttMsgUnsuback : MqttMsgBase
	{
		public MqttMsgUnsuback()
		{
			type = 11;
		}

		public static MqttMsgUnsuback Parse(byte fixedHeaderFirstByte, byte protocolVersion, IMqttNetworkChannel channel)
		{
			int num = 0;
			MqttMsgUnsuback mqttMsgUnsuback = new MqttMsgUnsuback();
			if (protocolVersion == 4 && (fixedHeaderFirstByte & 0xF) != 0)
			{
				throw new MqttClientException(MqttClientErrorCode.InvalidFlagBits);
			}
			byte[] array = new byte[MqttMsgBase.decodeRemainingLength(channel)];
			channel.Receive(array);
			mqttMsgUnsuback.messageId = (ushort)((array[num++] << 8) & 0xFF00);
			mqttMsgUnsuback.messageId |= array[num++];
			return mqttMsgUnsuback;
		}

		public override byte[] GetBytes(byte protocolVersion)
		{
			int num = 0;
			int num2 = 0;
			int num3 = 0;
			int num4 = 0;
			int index = 0;
			num2 += 2;
			num4 += num2 + num3;
			num = 1;
			int num5 = num4;
			do
			{
				num++;
				num5 /= 128;
			}
			while (num5 > 0);
			byte[] array = new byte[num + num2 + num3];
			if (protocolVersion == 4)
			{
				array[index++] = 176;
			}
			else
			{
				array[index++] = 176;
			}
			index = encodeRemainingLength(num4, array, index);
			array[index++] = (byte)((messageId >> 8) & 0xFF);
			array[index++] = (byte)(messageId & 0xFF);
			return array;
		}

		public override string ToString()
		{
			return GetTraceString("UNSUBACK", new object[1] { "messageId" }, new object[1] { messageId });
		}
	}
	public class MqttMsgUnsubscribe : MqttMsgBase
	{
		private string[] topics;

		public string[] Topics
		{
			get
			{
				return topics;
			}
			set
			{
				topics = value;
			}
		}

		public MqttMsgUnsubscribe()
		{
			type = 10;
		}

		public MqttMsgUnsubscribe(string[] topics)
		{
			type = 10;
			this.topics = topics;
			qosLevel = 1;
		}

		public static MqttMsgUnsubscribe Parse(byte fixedHeaderFirstByte, byte protocolVersion, IMqttNetworkChannel channel)
		{
			int num = 0;
			MqttMsgUnsubscribe mqttMsgUnsubscribe = new MqttMsgUnsubscribe();
			if (protocolVersion == 4 && (fixedHeaderFirstByte & 0xF) != 2)
			{
				throw new MqttClientException(MqttClientErrorCode.InvalidFlagBits);
			}
			int num2 = MqttMsgBase.decodeRemainingLength(channel);
			byte[] array = new byte[num2];
			channel.Receive(array);
			if (protocolVersion == 3)
			{
				mqttMsgUnsubscribe.qosLevel = (byte)((fixedHeaderFirstByte & 6) >> 1);
				mqttMsgUnsubscribe.dupFlag = (fixedHeaderFirstByte & 8) >> 3 == 1;
				mqttMsgUnsubscribe.retain = false;
			}
			mqttMsgUnsubscribe.messageId = (ushort)((array[num++] << 8) & 0xFF00);
			mqttMsgUnsubscribe.messageId |= array[num++];
			IList<string> list = new List<string>();
			do
			{
				int num3 = (array[num++] << 8) & 0xFF00;
				num3 |= array[num++];
				byte[] array2 = new byte[num3];
				Array.Copy(array, num, array2, 0, num3);
				num += num3;
				list.Add(new string(Encoding.UTF8.GetChars(array2)));
			}
			while (num < num2);
			mqttMsgUnsubscribe.topics = new string[list.Count];
			for (int i = 0; i < list.Count; i++)
			{
				mqttMsgUnsubscribe.topics[i] = list[i];
			}
			return mqttMsgUnsubscribe;
		}

		public override byte[] GetBytes(byte protocolVersion)
		{
			int num = 0;
			int num2 = 0;
			int num3 = 0;
			int num4 = 0;
			int num5 = 0;
			if (topics == null || topics.Length == 0)
			{
				throw new MqttClientException(MqttClientErrorCode.TopicsEmpty);
			}
			num2 += 2;
			int num6 = 0;
			byte[][] array = new byte[topics.Length][];
			for (num6 = 0; num6 < topics.Length; num6++)
			{
				if (topics[num6].Length < 1 || topics[num6].Length > 65535)
				{
					throw new MqttClientException(MqttClientErrorCode.TopicLength);
				}
				array[num6] = Encoding.UTF8.GetBytes(topics[num6]);
				num3 += 2;
				num3 += array[num6].Length;
			}
			num4 += num2 + num3;
			num = 1;
			int num7 = num4;
			do
			{
				num++;
				num7 /= 128;
			}
			while (num7 > 0);
			byte[] array2 = new byte[num + num2 + num3];
			if (protocolVersion == 4)
			{
				array2[num5++] = 162;
			}
			else
			{
				array2[num5] = (byte)(0xA0 | (qosLevel << 1));
				array2[num5] |= (byte)(dupFlag ? 8 : 0);
				num5++;
			}
			num5 = encodeRemainingLength(num4, array2, num5);
			if (messageId == 0)
			{
				throw new MqttClientException(MqttClientErrorCode.WrongMessageId);
			}
			array2[num5++] = (byte)((messageId >> 8) & 0xFF);
			array2[num5++] = (byte)(messageId & 0xFF);
			num6 = 0;
			for (num6 = 0; num6 < topics.Length; num6++)
			{
				array2[num5++] = (byte)((array[num6].Length >> 8) & 0xFF);
				array2[num5++] = (byte)(array[num6].Length & 0xFF);
				Array.Copy(array[num6], 0, array2, num5, array[num6].Length);
				num5 += array[num6].Length;
			}
			return array2;
		}

		public override string ToString()
		{
			return GetTraceString("UNSUBSCRIBE", new object[2] { "messageId", "topics" }, new object[2] { messageId, topics });
		}
	}
	public class MqttMsgUnsubscribedEventArgs : EventArgs
	{
		private ushort messageId;

		public ushort MessageId
		{
			get
			{
				return messageId;
			}
			internal set
			{
				messageId = value;
			}
		}

		public MqttMsgUnsubscribedEventArgs(ushort messageId)
		{
			this.messageId = messageId;
		}
	}
	public class MqttMsgUnsubscribeEventArgs : EventArgs
	{
		private ushort messageId;

		private string[] topics;

		public ushort MessageId
		{
			get
			{
				return messageId;
			}
			internal set
			{
				messageId = value;
			}
		}

		public string[] Topics
		{
			get
			{
				return topics;
			}
			internal set
			{
				topics = value;
			}
		}

		public MqttMsgUnsubscribeEventArgs(ushort messageId, string[] topics)
		{
			this.messageId = messageId;
			this.topics = topics;
		}
	}
}
namespace uPLibrary.Networking.M2Mqtt.Internal
{
	public abstract class InternalEvent
	{
	}
	public class MsgInternalEvent : InternalEvent
	{
		protected MqttMsgBase msg;

		public MqttMsgBase Message
		{
			get
			{
				return msg;
			}
			set
			{
				msg = value;
			}
		}

		public MsgInternalEvent(MqttMsgBase msg)
		{
			this.msg = msg;
		}
	}
	public class MsgPublishedInternalEvent : MsgInternalEvent
	{
		private bool isPublished;

		public bool IsPublished
		{
			get
			{
				return isPublished;
			}
			internal set
			{
				isPublished = value;
			}
		}

		public MsgPublishedInternalEvent(MqttMsgBase msg, bool isPublished)
			: base(msg)
		{
			this.isPublished = isPublished;
		}
	}
}
namespace uPLibrary.Networking.M2Mqtt.Exceptions
{
	public class MqttClientException : Exception
	{
		private MqttClientErrorCode errorCode;

		public MqttClientErrorCode ErrorCode
		{
			get
			{
				return errorCode;
			}
			set
			{
				errorCode = value;
			}
		}

		public MqttClientException(MqttClientErrorCode errorCode)
		{
			this.errorCode = errorCode;
		}
	}
	public enum MqttClientErrorCode
	{
		WillWrong = 1,
		KeepAliveWrong,
		TopicWildcard,
		TopicLength,
		QosNotAllowed,
		TopicsEmpty,
		QosLevelsEmpty,
		TopicsQosLevelsNotMatch,
		WrongBrokerMessage,
		WrongMessageId,
		InflightQueueFull,
		InvalidFlagBits,
		InvalidConnectFlags,
		InvalidClientId,
		InvalidProtocolName
	}
	public class MqttCommunicationException : Exception
	{
		public MqttCommunicationException()
		{
		}

		public MqttCommunicationException(Exception e)
			: base(string.Empty, e)
		{
		}
	}
	public class MqttConnectionException : Exception
	{
		public MqttConnectionException(string message, Exception innerException)
			: base(message, innerException)
		{
		}
	}
	public class MqttTimeoutException : Exception
	{
	}
}
