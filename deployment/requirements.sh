pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

echo "y" | pip uninstall silvaengine_utility && pip install git+ssh://git@github.com/ideabosque/silvaengine_utility.git@main#egg=silvaengine_utility
echo "y" | pip uninstall event_triggers && pip install git+ssh://git@github.com/ideabosque/event_triggers.git@main#egg=event_triggers
echo "y" | pip uninstall silvaengine_authorizer && pip install git+ssh://git@github.com/ideabosque/silvaengine_authorizer.git@main#egg=silvaengine_authorizer
echo "y" | pip uninstall silvaengine_base && pip install git+ssh://git@github.com/ideabosque/silvaengine_base.git@main#egg=silvaengine_base

python3.8 cloudformation_stack.py silvaengine