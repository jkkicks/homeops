ANSIBLE_CONFIG := bootstrap/ansible/ansible.cfg
INVENTORY := bootstrap/ansible/inventory/hosts.yml
PLAYBOOKS := bootstrap/ansible/playbooks

export ANSIBLE_CONFIG

.PHONY: age-key greenfield join verify lint

age-key:
	@test ! -e sops_age_key.txt || { echo "sops_age_key.txt already exists" >&2; exit 1; }
	@test ! -e age.pubkey || { echo "age.pubkey already exists; refusing to replace it" >&2; exit 1; }
	@age-keygen -o sops_age_key.txt
	@age-keygen -y sops_age_key.txt > age.pubkey
	@chmod 600 sops_age_key.txt

greenfield:
	ansible-playbook -i $(INVENTORY) $(PLAYBOOKS)/greenfield.yml

join:
	ansible-playbook -i $(INVENTORY) $(PLAYBOOKS)/join.yml

verify:
	ansible-playbook -i $(INVENTORY) $(PLAYBOOKS)/verify.yml

lint:
	bash scripts/validate-layout.sh
	bash scripts/test-ansible-skeleton.sh
	ansible-lint bootstrap/ansible
	ansible-playbook -i $(INVENTORY) --syntax-check $(PLAYBOOKS)/greenfield.yml
	ansible-playbook -i $(INVENTORY) --syntax-check $(PLAYBOOKS)/join.yml
	ansible-playbook -i $(INVENTORY) --syntax-check $(PLAYBOOKS)/verify.yml
