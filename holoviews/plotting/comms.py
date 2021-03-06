import uuid

import param
from ipykernel.comm import Comm as IPyComm
from IPython import get_ipython


class Comm(param.Parameterized):
    """
    Comm encompasses any uni- or bi-directional connection between
    a python process and a frontend allowing passing of messages
    between the two. A Comms class must implement methods
    send data and handle received message events.

    If the Comm has to be set up on the frontend a template to
    handle the creation of the comms channel along with a message
    handler to process incoming messages must be supplied.

    The template must accept three arguments:

    * comms_target - A unique id to register to register as the
                     comms target.
    * msg_handler -  JS code which has the msg variable in scope and
                     performs appropriate action for the supplied message.
    * init_frame  -  The initial frame to render on the frontend.
    """

    template = ''

    def __init__(self, plot, target=None, on_msg=None):
        """
        Initializes a Comms object
        """
        self.target = target if target else uuid.uuid4().hex
        self._plot = plot
        self._on_msg = on_msg
        self._comm = None


    def init(self, on_msg=None):
        """
        Initializes comms channel.
        """


    def send(self, data):
        """
        Sends data to the frontend
        """


    @classmethod
    def decode(cls, msg):
        """
        Decode incoming message, e.g. by parsing json.
        """
        return msg


    @property
    def comm(self):
        if not self._comm:
            raise ValueError('Comm has not been initialized')
        return self._comm


    def _handle_msg(self, msg):
        """
        Decode received message before passing it to on_msg callback
        if it has been defined.
        """
        if self._on_msg:
            self._on_msg(self.decode(msg))


class JupyterComm(Comm):
    """
    JupyterComm provides a Comm for the notebook which is initialized
    the first time data is pushed to the frontend.
    """

    template = """
    <script>
      function msg_handler(msg) {{
        var msg = msg.content.data;
        {msg_handler}
      }}

      if ((window.Jupyter !== undefined) && (Jupyter.notebook.kernel !== undefined)) {{
        comm_manager = Jupyter.notebook.kernel.comm_manager;
        comm_manager.register_target("{comms_target}", function(comm) {{ comm.on_msg(msg_handler);}});
      }}
    </script>

    <div id="fig_{comms_target}">
      {init_frame}
    </div>
    """

    def init(self):
        if self._comm:
            return
        self._comm = IPyComm(target_name=self.target, data={})
        self._comm.on_msg(self._handle_msg)


    @classmethod
    def decode(cls, msg):
        return msg['content']['data']


    def send(self, data):
        """
        Pushes data across comm socket.
        """
        if not self._comm:
            self.init()
        self.comm.send(data)



class JupyterCommJS(Comm):
    """
    JupyterCommJS provides a comms channel for the Jupyter notebook,
    which is initialized on the frontend. This allows sending events
    initiated on the frontend to python.
    """

    template = """
    <script>
      function msg_handler(msg) {{
        var msg = msg.content.data;
        {msg_handler}
      }}

      if ((window.Jupyter !== undefined) && (Jupyter.notebook.kernel !== undefined)) {{
        var comm_manager = Jupyter.notebook.kernel.comm_manager;
        comm = comm_manager.new_comm("{comms_target}", {{}}, {{}}, {{}}, "{comms_target}");
        comm.on_msg(msg_handler);
      }}
    </script>

    <div id="fig_{comms_target}">
      {init_frame}
    </div>
    """

    def __init__(self, plot, target=None, on_msg=None):
        """
        Initializes a Comms object
        """
        super(JupyterComm, self).__init__(plot, target, on_msg)
        self.manager = get_ipython().kernel.comm_manager
        self.manager.register_target(self.target, self._handle_open)


    def _handle_open(self, comm, msg):
        self._comm = comm
        self._comm.on_msg(self._handle_msg)


    def send(self, data):
        """
        Pushes data across comm socket.
        """
        self.comm.send(data)

